/**
 * Paddy Farming Assistant - Field Health Analysis History Service
 * 
 * Manages persistent client-side analysis history using browser IndexedDB.
 * - Stores analysis history locally on the current device/browser.
 * - Associates each record with the authenticated farmer's unique user ID.
 * - Enforces strict per-account isolation (Farmer A never sees Farmer B's records).
 * - Preserves history across logout and browser restart.
 * - Zero database writes: Does not transmit field coordinates or analysis history to PostgreSQL.
 * - Provides full snapshot storage for instant offline viewing without rerunning satellite queries.
 */

const DB_NAME = 'PaddyFieldHealthDB';
const DB_VERSION = 1;
const STORE_NAME = 'analysis_history';

let _dbPromise = null;

/**
 * Opens or upgrades the persistent IndexedDB database.
 * Returns a Promise that resolves with the IDBDatabase instance.
 */
export function openFieldHealthDB() {
  if (typeof window === 'undefined' || !window.indexedDB) {
    return Promise.reject(new Error('IndexedDB is not supported in this browser environment.'));
  }

  if (_dbPromise) return _dbPromise;

  _dbPromise = new Promise((resolve, reject) => {
    try {
      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
          // Secondary indexes for queries
          store.createIndex('userId', 'userId', { unique: false });
          store.createIndex('fieldId', 'fieldId', { unique: false });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('user_timestamp', ['userId', 'timestamp'], { unique: false });
        }
      };

      request.onsuccess = (event) => {
        const db = event.target.result;
        // Handle database close/abort gracefully
        db.onversionchange = () => {
          db.close();
          _dbPromise = null;
        };
        resolve(db);
      };

      request.onerror = (event) => {
        _dbPromise = null;
        reject(event.target.error || new Error('Failed to open IndexedDB database.'));
      };
    } catch (err) {
      _dbPromise = null;
      reject(err);
    }
  });

  return _dbPromise;
}

/**
 * Resolves the authenticated farmer's unique user ID from session state.
 * Fallbacks safely to username or 'anonymous_farmer' if unauthenticated.
 */
export function getCurrentFarmerId() {
  if (typeof window === 'undefined') return 'anonymous_farmer';

  try {
    // 1. Check tab-scoped sessionStorage farmerId (set by auth.js)
    const fid = sessionStorage.getItem('farmerId');
    if (fid && fid.trim()) return fid.trim();

    // 2. Check tab-scoped sessionStorage username
    const uname = sessionStorage.getItem('username');
    if (uname && uname.trim()) return `user_${uname.trim()}`;

    // 3. Check window.getAuthUser() if available
    if (typeof window.getAuthUser === 'function') {
      const u = window.getAuthUser();
      if (u?.farmer_id) return u.farmer_id;
      if (u?.id) return u.id;
      if (u?.username) return `user_${u.username}`;
    }
  } catch (err) {
    console.warn('Unable to resolve current farmer ID:', err);
  }

  return 'anonymous_farmer';
}

/**
 * Resolves the authenticated farmer's human-readable name or username.
 */
export function getCurrentFarmerName() {
  if (typeof window === 'undefined') return 'Farmer';

  try {
    const uname = sessionStorage.getItem('username');
    if (uname && uname.trim()) return uname.trim();

    if (typeof window.getAuthUser === 'function') {
      const u = window.getAuthUser();
      if (u?.username) return u.username;
    }
  } catch (_) {}

  return 'Farmer';
}

/**
 * Formats a Date object or timestamp into an Indian Standard Time (IST) display string.
 * Example: "07 Nov 2026, 09:30 AM"
 */
export function formatAnalysisDate(timestampOrIso) {
  try {
    const d = new Date(timestampOrIso);
    if (isNaN(d.getTime())) return 'Recently';

    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch (_) {
    return 'Recently';
  }
}

/**
 * Persists a field health analysis record to local IndexedDB.
 * Associates the record strictly with the authenticated farmer's userId.
 * 
 * @param {object} analysisData - Full analysis snapshot (indices, classifications, timesteps, etc.)
 * @returns {Promise<object>} The stored record with unique ID and timestamp
 */
export async function saveAnalysisHistoryRecord(analysisData) {
  if (!analysisData) {
    throw new Error('Analysis data cannot be empty.');
  }

  const userId = analysisData.userId || getCurrentFarmerId();
  const username = analysisData.username || getCurrentFarmerName();
  const timestamp = analysisData.timestamp || Date.now();
  const id = analysisData.id || `fha_${timestamp}_${Math.random().toString(36).substring(2, 8)}`;
  const displayDate = analysisData.displayDate || formatAnalysisDate(timestamp);

  const record = {
    ...analysisData,
    id,
    userId,
    username,
    timestamp,
    displayDate,
    savedAt: new Date().toISOString(),
  };

  const db = await openFieldHealthDB();

  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);

      const request = store.put(record);

      request.onsuccess = () => resolve(record);
      request.onerror = (e) => reject(e.target.error || new Error('Failed to save record to IndexedDB.'));
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Retrieves all stored field health analysis records for a specific farmer.
 * Sorts records in reverse chronological order (newest first).
 * Strictly guarantees that no other farmer's records are returned.
 * 
 * @param {string} [userId] - Optional farmer ID; defaults to current authenticated farmer
 * @returns {Promise<Array<object>>} List of historical analysis records
 */
export async function getFarmerAnalysisHistory(userId) {
  const targetUserId = userId || getCurrentFarmerId();
  if (!targetUserId) return [];

  const db = await openFieldHealthDB();

  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const index = store.index('userId');

      const request = index.getAll(IDBKeyRange.only(targetUserId));

      request.onsuccess = () => {
        const list = request.result || [];
        // Sort newest first by timestamp
        list.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
        resolve(list);
      };

      request.onerror = (e) => reject(e.target.error || new Error('Failed to load farmer history from IndexedDB.'));
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Retrieves a single analysis record by its primary key.
 * 
 * @param {string} id - Record ID
 * @returns {Promise<object|null>}
 */
export async function getAnalysisHistoryById(id) {
  if (!id) return null;

  const db = await openFieldHealthDB();

  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result || null);
      request.onerror = (e) => reject(e.target.error);
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Deletes an individual analysis record from IndexedDB.
 * Enforces ownership check: record must belong to the specified userId.
 * 
 * @param {string} id - Record ID
 * @param {string} [userId] - Current authenticated farmer ID
 * @returns {Promise<boolean>} True if deleted, false if not found
 */
export async function deleteAnalysisHistoryRecord(id, userId) {
  if (!id) return false;
  const currentId = userId || getCurrentFarmerId();

  const db = await openFieldHealthDB();

  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);

      const getReq = store.get(id);

      getReq.onsuccess = () => {
        const item = getReq.result;
        if (!item) {
          resolve(false);
          return;
        }

        // Ownership enforcement: prevent accidental cross-account deletions
        if (currentId && item.userId && item.userId !== currentId) {
          reject(new Error('Permission denied: You can only delete your own analysis records.'));
          return;
        }

        const delReq = store.delete(id);
        delReq.onsuccess = () => resolve(true);
        delReq.onerror = (e) => reject(e.target.error);
      };

      getReq.onerror = (e) => reject(e.target.error);
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Clears all analysis history records belonging to the current farmer.
 * Leaves records belonging to other farmer accounts completely untouched.
 * 
 * @param {string} [userId] - Optional farmer ID; defaults to current authenticated farmer
 * @returns {Promise<number>} Number of records deleted
 */
export async function clearFarmerAnalysisHistory(userId) {
  const targetUserId = userId || getCurrentFarmerId();
  if (!targetUserId) return 0;

  const db = await openFieldHealthDB();

  return new Promise((resolve, reject) => {
    try {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const index = store.index('userId');

      const req = index.openCursor(IDBKeyRange.only(targetUserId));
      let count = 0;

      req.onsuccess = (e) => {
        const cursor = e.target.result;
        if (cursor) {
          cursor.delete();
          count++;
          cursor.continue();
        } else {
          resolve(count);
        }
      };

      req.onerror = (e) => reject(e.target.error);
    } catch (err) {
      reject(err);
    }
  });
}

// Global browser object exposure for non-module vanilla scripts
if (typeof window !== 'undefined') {
  window.FieldHealthHistory = {
    openDB: openFieldHealthDB,
    getCurrentFarmerId,
    getCurrentFarmerName,
    formatDate: formatAnalysisDate,
    saveRecord: saveAnalysisHistoryRecord,
    getHistory: getFarmerAnalysisHistory,
    getRecordById: getAnalysisHistoryById,
    deleteRecord: deleteAnalysisHistoryRecord,
    clearHistory: clearFarmerAnalysisHistory,
  };
}

