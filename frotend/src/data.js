// ============================================================================
// STEP 3: CENTRAL SAMPLE DATA & DATA ACCESS LAYER
// ============================================================================
// ALL DATA BELOW IS SAMPLE DATA FOR FRONTEND TESTING ONLY.
// THERE IS NO REAL BACKEND CONNECTION AT THIS STAGE.
// ============================================================================

const SAMPLE_DATA = {
  // 1. Farmer Profiles
  farmer: {
    id: "f1",
    name: "Jaya",
    village: "Obullavari Palli",
    farmName: "Jaya Paddy Farm",
    isNew: false
  },
  
  emptyFarmer: {
    id: "f2",
    name: "New Farmer",
    village: "Unknown",
    farmName: "My New Farm",
    isNew: true
  },

  // 2. Fields
  fields: [
    {
      id: "field-1",
      name: "North Plot",
      status: "Healthy",
      crop: "Paddy (Samba Mahsuri)",
      variety: "Samba Mahsuri",
      sowingDate: "2023-08-15",
      location: "Near canal",
      satelliteAvailable: true
    },
    {
      id: "field-2",
      name: "East Plot",
      status: "Needs Attention",
      crop: "Paddy (BPT 5204)",
      variety: "BPT 5204",
      sowingDate: "2023-08-20",
      location: "Highway side",
      satelliteAvailable: true
    },
    {
      id: "field-3",
      name: "South Plot",
      status: "High Risk",
      crop: "Paddy (Samba Mahsuri)",
      variety: "Samba Mahsuri",
      sowingDate: "2023-09-01",
      location: "Lowland area",
      satelliteAvailable: true
    },
    {
      id: "field-4",
      name: "West New Plot",
      status: "Unknown",
      crop: "Paddy",
      variety: "Unknown",
      sowingDate: "2023-09-10",
      location: "Hill side",
      satelliteAvailable: false // NO SATELLITE DATA CASE
    }
  ],

  // 3. Field Health Data (Detailed for Step 6)
  fieldHealth: {
    "field-1": {
      trend: [
        { week: 'Week 1', ndvi: 0.2, moisture: 60 },
        { week: 'Week 2', ndvi: 0.4, moisture: 65 },
        { week: 'Week 3', ndvi: 0.6, moisture: 70 },
        { week: 'Week 4', ndvi: 0.75, moisture: 75 }
      ],
      healthLevel: "Good",
      satellite: { available: true, lastChecked: "Oct 24, 2023", nextUpdate: "Oct 29, 2023" },
      alerts: [],
      details: { ndvi: "0.75", ndre: "0.68", gndvi: "0.72", monitoringDate: "Oct 24, 2023" }
    },
    "field-2": {
      trend: [
        { week: 'Week 1', ndvi: 0.2, moisture: 50 },
        { week: 'Week 2', ndvi: 0.35, moisture: 45 },
        { week: 'Week 3', ndvi: 0.45, moisture: 40 },
        { week: 'Week 4', ndvi: 0.5, moisture: 35 }
      ],
      healthLevel: "Moderate",
      satellite: { available: true, lastChecked: "Oct 24, 2023", nextUpdate: "Oct 29, 2023" },
      alerts: [
        { title: "Moisture levels dropping", explanation: "Soil moisture has decreased consistently over the last two weeks.", check: "Check irrigation lines and consider a watering cycle." }
      ],
      details: { ndvi: "0.50", ndre: "0.45", gndvi: "0.48", monitoringDate: "Oct 24, 2023" }
    },
    "field-3": {
      trend: [
        { week: 'Week 1', ndvi: 0.2, moisture: 70 },
        { week: 'Week 2', ndvi: 0.3, moisture: 80 },
        { week: 'Week 3', ndvi: 0.25, moisture: 85 },
        { week: 'Week 4', ndvi: 0.2, moisture: 90 }
      ],
      healthLevel: "Low",
      satellite: { available: true, lastChecked: "Oct 24, 2023", nextUpdate: "Oct 29, 2023" },
      alerts: [
        { title: "Crop health has decreased", explanation: "Your crop health has changed compared with the previous check.", check: "Walk through the field and look for yellowing or damaged leaves." },
        { title: "High moisture detected", explanation: "The field appears waterlogged in satellite imagery.", check: "Check drainage and ensure water isn't pooling." }
      ],
      details: { ndvi: "0.20", ndre: "0.22", gndvi: "0.19", monitoringDate: "Oct 24, 2023" }
    },
    "field-4": {
      trend: [],
      healthLevel: "Unknown",
      satellite: { available: false, lastChecked: null, nextUpdate: null },
      alerts: [],
      details: { ndvi: "N/A", ndre: "N/A", gndvi: "N/A", monitoringDate: "N/A" }
    }
  },

  // 4. Disease Results
  diseaseResults: [
    {
      id: "d1",
      result: "Brown Plant Hopper",
      friendlyName: "Brown Plant Hopper (BPH)",
      confidence: 0.92,
      cropStatus: "High Risk",
      info: "Insects are draining sap from the base of the plant. Requires immediate treatment."
    },
    {
      id: "d2",
      result: "Leaf Blast",
      friendlyName: "Rice Blast Disease",
      confidence: 0.85,
      cropStatus: "Needs Attention",
      info: "Fungal infection causing diamond-shaped spots on leaves. Needs fungicide application."
    },
    {
      id: "d3",
      result: "Unknown",
      friendlyName: "We are not sure", // EDGE CASE
      confidence: 0.30,
      cropStatus: "Unknown",
      info: "The image is not clear enough or doesn't match known diseases. Please take another photo."
    }
  ],

  // 4b. Crop Insights Data
  cropInsights: {
    "insight-1": {
      id: "insight-1",
      condition: "Brown Plant Hopper",
      confidence: "High confidence",
      status: "High Risk",
      hasFieldData: true,
      influences: {
        leafAppearance: "High",
        cropHealthChange: "Medium",
        fieldCondition: "High"
      },
      timeline: [
        { date: "June 10", change: "Crop health was good", desc: "No issues detected in field." },
        { date: "July 05", change: "Some changes were noticed", desc: "Mild yellowing started appearing." },
        { date: "July 25", change: "Crop health needs attention", desc: "Significant damage at the base of plants." }
      ],
      symptoms: [
        "Yellowing leaves",
        "Drying or wilting at base",
        "Presence of small insects"
      ],
      explanation: "The presence of drying at the plant base combined with the recent drop in overall field health suggests a pest issue. The field's high moisture level creates a favorable environment for Brown Plant Hoppers."
    },
    "insight-photo-only": {
      id: "insight-photo-only",
      condition: "Leaf Blast",
      confidence: "Medium confidence",
      status: "Needs Attention",
      hasFieldData: false,
      influences: {
        leafAppearance: "High",
        cropHealthChange: "N/A",
        fieldCondition: "N/A"
      },
      timeline: [],
      symptoms: [
        "Diamond-shaped spots",
        "Brown borders on spots",
        "Leaf damage"
      ],
      explanation: "The leaf shows distinct diamond-shaped spots which are a strong visual indicator of Leaf Blast. Since this check only used a photo, we cannot confirm if the surrounding field conditions are contributing to the spread."
    }
  },

  // 5. Buyers (Enriched for Step 9 & Step 11H)
  buyers: [
    { id: "b1", name: "Sri Lakshmi Traders", business_name: "Sri Lakshmi Traders", buyer_type: "trader", district: "Kurnool", state: "Andhra Pradesh", location: "Kurnool Market", address_summary: "Market Yard, Kurnool", lat: null, lng: null, riceType: "Samba Mahsuri", priceNum: 2400, price: "\u20B92,400/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543210" },
    { id: "b2", name: "Annapurna Rice Mill", business_name: "Annapurna Rice Mill", buyer_type: "mill", district: "SPSR Nellore", state: "Andhra Pradesh", location: "Nellore", address_summary: "Indukurpet Road, Nellore", lat: null, lng: null, riceType: "BPT 5204", priceNum: 2350, price: "\u20B92,350/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543211" },
    { id: "b3", name: "Farmers Co-op", business_name: "Farmers Co-op", buyer_type: "fpo", district: "Krishna", state: "Andhra Pradesh", location: "Local Mandi", address_summary: "Nagayalanka, Krishna", lat: null, lng: null, riceType: "All varieties", priceNum: 2300, price: "\u20B92,300/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543212" },
    { id: "b4", name: "Venkat Exports", business_name: "Venkat Exports", buyer_type: "mill", district: "Kakinada", state: "Andhra Pradesh", location: "Kakinada", address_summary: "Ramanayyapeta, Kakinada", lat: null, lng: null, riceType: "Samba Mahsuri", priceNum: 2600, price: "\u20B92,600/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543213" },
    { id: "b5", name: "Kisan Buyers Group", business_name: "Kisan Buyers Group", buyer_type: "fpo", district: "Guntur", state: "Andhra Pradesh", location: "Guntur", address_summary: "Tenali Road, Guntur", lat: null, lng: null, riceType: "BPT 5204", priceNum: 2450, price: "\u20B92,450/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543214" },
    { id: "b6", name: "Paddy Gold Mills", business_name: "Paddy Gold Mills", buyer_type: "mill", district: "West Godavari", state: "Andhra Pradesh", location: "Eluru", address_summary: "Beside Lions Club, Eluru", lat: null, lng: null, riceType: "Samba Mahsuri", priceNum: 2500, price: "\u20B92,500/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543215" },
    { id: "b7", name: "Ravi Rice Traders", business_name: "Ravi Rice Traders", buyer_type: "trader", district: "SPSR Nellore", state: "Andhra Pradesh", location: "Nellore", address_summary: "Nawabpet, Nellore", lat: null, lng: null, riceType: "BPT 5204", priceNum: 2380, price: "\u20B92,380/qtl", distance: null, distance_km: null, verification_status: "pending", contact: "9876543216" },
    { id: "b8", name: "AP Rice Hub", business_name: "AP Rice Hub", buyer_type: "government_agency", district: "Kakinada", state: "Andhra Pradesh", location: "Kakinada", address_summary: "Civil Supplies Bhavan, Kakinada", lat: null, lng: null, riceType: "All varieties", priceNum: 2420, price: "\u20B92,420/qtl", distance: null, distance_km: null, verification_status: "verified", contact: "9876543217" }
  ],

  // 6. Rice Prices (Enriched for Step 9)
  riceVarieties: ["Samba Mahsuri", "BPT 5204", "Common Rice"],
  prices: [
    { date: "30 Sep 2026", variety: "Samba Mahsuri", priceNum: 2450, price: "\u20B92,450/qtl", trend: "up" },
    { date: "30 Sep 2026", variety: "BPT 5204", priceNum: 2350, price: "\u20B92,350/qtl", trend: "stable" },
    { date: "30 Sep 2026", variety: "Common Rice", priceNum: 2100, price: "\u20B92,100/qtl", trend: "down" }
  ],
  priceHistory: {
    "Samba Mahsuri": [
      { month: "May", price: 2200 }, { month: "Jun", price: 2280 },
      { month: "Jul", price: 2320 }, { month: "Aug", price: 2380 },
      { month: "Sep", price: 2450 }
    ],
    "BPT 5204": [
      { month: "May", price: 2150 }, { month: "Jun", price: 2200 },
      { month: "Jul", price: 2250 }, { month: "Aug", price: 2300 },
      { month: "Sep", price: 2350 }
    ],
    "Common Rice": [
      { month: "May", price: 2200 }, { month: "Jun", price: 2180 },
      { month: "Jul", price: 2150 }, { month: "Aug", price: 2120 },
      { month: "Sep", price: 2100 }
    ]
  },
  marketLastUpdated: "30 Sep 2026",

  // 7. History (Detailed for Step 8)
  history: [
    { 
      id: "h1", 
      date: "2023-10-12", 
      fieldId: "field-1",
      field: "North Plot",
      result: "Healthy", 
      confidence: "98% — High confidence",
      fieldHealth: "Healthy",
      symptoms: ["No visible signs of disease or pest infestation.", "Leaves show good color and structure."],
      recommendations: "Maintain your current watering and nutrient routine. Keep monitoring regularly.",
      hasPhoto: true
    },
    { 
      id: "h2", 
      date: "2023-10-05", 
      fieldId: "field-2",
      field: "East Plot",
      result: "Leaf Blast", 
      confidence: "85% — Medium confidence",
      fieldHealth: "Needs Attention",
      symptoms: ["Diamond-shaped spots", "Brown borders on spots", "Leaf damage"],
      recommendations: "Apply recommended fungicide. Avoid excess nitrogen fertilizer application.",
      hasPhoto: true
    },
    { 
      id: "h3", 
      date: "2023-09-28", 
      fieldId: "field-3",
      field: "South Plot",
      result: "Brown Plant Hopper", 
      confidence: "92% — High confidence",
      fieldHealth: "High Risk",
      symptoms: ["Yellowing leaves", "Drying or wilting at base", "Presence of small insects"],
      recommendations: "Requires immediate treatment. Drain the field for 3-4 days to reduce humidity. Apply recommended pesticide at the base of the plants.",
      hasPhoto: true
    },
    { 
      id: "h4", 
      date: "2023-09-15", 
      fieldId: "field-2",
      field: "East Plot",
      result: "Healthy", 
      confidence: "90% — High confidence",
      fieldHealth: "Healthy",
      symptoms: ["Healthy growth"],
      recommendations: "Continue standard care.",
      hasPhoto: true
    }
  ],

  // 8. Weather (4-Day Forecast)
  weather: [
    { date: "Today", temp: "32\u00B0C", condition: "Partly cloudy", rainfall: "0%" },
    { date: "Tomorrow", temp: "30\u00B0C", condition: "Cloudy", rainfall: "20%" },
    { date: "Day 3", temp: "28\u00B0C", condition: "Rain", rainfall: "80%" },
    { date: "Day 4", temp: "29\u00B0C", condition: "Scattered Showers", rainfall: "40%" }
  ],

  // 9. General Alerts (For Home Page)
  generalAlerts: [
    { title: "Heavy Rain Expected", explanation: "Heavy rainfall is expected tomorrow afternoon.", status: "Needs Attention" },
    { title: "Market Price Up", explanation: "BPT 5204 prices have increased by \u20B950/qtl.", status: "Healthy" },
    { title: "Pest Warning", explanation: "Brown Plant Hopper reported in neighboring farms.", status: "High Risk" }
  ]
};

// ============================================================================
// DATA ACCESS LAYER
// ============================================================================
// The frontend screens must call these functions instead of reading the 
// sample data directly. When the real backend is ready, only these functions
// will need to be updated.
// ============================================================================

const ARTIFICIAL_DELAY_MS = 600; // Small delay to test loading states

// Helper to simulate network delay
const withDelay = (data) => {
  return new Promise(resolve => {
    setTimeout(() => resolve(data), ARTIFICIAL_DELAY_MS);
  });
};

window.DataAccess = {
  // Get farmer profile (pass true to simulate a brand new empty farmer)
  getFarmer: (isEmpty = false) => {
    return withDelay(isEmpty ? SAMPLE_DATA.emptyFarmer : SAMPLE_DATA.farmer);
  },

  getFields: () => {
    return withDelay(SAMPLE_DATA.fields);
  },

  getFieldHealth: (fieldId) => {
    return withDelay(SAMPLE_DATA.fieldHealth[fieldId] || null);
  },

  getDiseaseResults: () => {
    return withDelay(SAMPLE_DATA.diseaseResults);
  },

  getCropInsight: (insightId) => {
    return withDelay(SAMPLE_DATA.cropInsights[insightId] || null);
  },

  // Useful for specifically fetching the "not sure" edge case
  getUncertainDiseaseResult: () => {
    return withDelay(SAMPLE_DATA.diseaseResults.find(d => d.friendlyName === "We are not sure"));
  },

  getBuyers: async (filter = {}) => {
    try {
      let url = "http://127.0.0.1:8000/buyers?limit=100";
      if (filter.district) url += `&district=${encodeURIComponent(filter.district)}`;
      if (filter.buyer_type) url += `&buyer_type=${encodeURIComponent(filter.buyer_type)}`;
      
      const res = await fetch(url, { signal: AbortSignal.timeout(1500) });
      if (res.ok) {
        const payload = await res.json();
        if (payload && Array.isArray(payload.items) && payload.items.length > 0) {
          return payload.items.map(b => ({
            id: b.id,
            name: b.business_name,
            business_name: b.business_name,
            buyer_type: b.buyer_type,
            district: b.district,
            state: b.state,
            location: `${b.district}, ${b.state}`,
            address_summary: b.address_summary || `${b.district}, Andhra Pradesh`,
            contact_person: b.contact_person,
            contact_phone: b.contact_phone,
            contact: b.contact_phone || b.contact_person || 'District Procurement Desk',
            preferred_varieties: b.preferred_varieties || [],
            riceType: (b.preferred_varieties && b.preferred_varieties[0]) || 'All varieties',
            priceNum: 2400,
            price: '₹2,320 – ₹2,450/qtl',
            verification_status: b.verification_status || 'verified',
            distance: null, // No fabricated distance
            distance_km: null,
            // Raw coordinates omitted from farmer-facing objects
            lat: null,
            lng: null,
          }));
        }
      }
    } catch (_err) {
      // Backend offline or timeout; fall back to sanitized sample buyers
    }
    return withDelay(SAMPLE_DATA.buyers);
  },

  getNearbyBuyers: async (lat, lon, radius_km = 50) => {
    try {
      const url = `http://127.0.0.1:8000/buyers/nearby?lat=${lat}&lon=${lon}${radius_km ? `&radius_km=${radius_km}` : ''}&limit=50`;
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const payload = await res.json();
        return {
          total: payload.total || 0,
          items: (payload.items || []).map(b => ({
            id: b.id,
            name: b.business_name,
            business_name: b.business_name,
            buyer_type: b.buyer_type,
            district: b.district,
            state: b.state,
            location: `${b.district}, ${b.state}`,
            address_summary: b.address_summary || `${b.district}, Andhra Pradesh`,
            contact_person: b.contact_person,
            contact_phone: b.contact_phone,
            contact: b.contact_phone || b.contact_person || 'District Procurement Desk',
            preferred_varieties: b.preferred_varieties || [],
            riceType: (b.preferred_varieties && b.preferred_varieties[0]) || 'All varieties',
            priceNum: 2400,
            price: '₹2,320 – ₹2,450/qtl',
            verification_status: b.verification_status || 'verified',
            distance: b.distance_km,
            distance_km: b.distance_km,
            // Raw coordinates omitted from farmer-facing objects
            lat: null,
            lng: null,
          }))
        };
      }
    } catch (_err) {
      // Safe empty response on network error
    }
    return { total: 0, items: [] };
  },

  getPrices: () => {
    return withDelay(SAMPLE_DATA.prices);
  },

  getRiceVarieties: () => {
    return withDelay(SAMPLE_DATA.riceVarieties);
  },

  getPriceHistory: (variety) => {
    return withDelay(SAMPLE_DATA.priceHistory[variety] || []);
  },

  getMarketLastUpdated: () => {
    return withDelay(SAMPLE_DATA.marketLastUpdated);
  },

  getHistory: (isEmpty = false) => {
    return withDelay(isEmpty ? [] : SAMPLE_DATA.history);
  },

  getWeather: () => {
    return withDelay(SAMPLE_DATA.weather);
  },

  getAlerts: () => {
    return withDelay(SAMPLE_DATA.generalAlerts);
  },

  getField: (id) => {
    return withDelay(SAMPLE_DATA.fields.find(f => f.id === id));
  },

  saveField: (fieldData) => {
    const newField = {
      id: "field-" + Date.now(),
      status: "Healthy", // Default for new fields
      satelliteAvailable: true,
      ...fieldData
    };
    SAMPLE_DATA.fields.push(newField);
    return withDelay(newField);
  },

  updateField: (id, fieldData) => {
    const index = SAMPLE_DATA.fields.findIndex(f => f.id === id);
    if (index !== -1) {
      SAMPLE_DATA.fields[index] = { ...SAMPLE_DATA.fields[index], ...fieldData };
      return withDelay(SAMPLE_DATA.fields[index]);
    }
    return withDelay(null);
  },

  deleteField: (id) => {
    SAMPLE_DATA.fields = SAMPLE_DATA.fields.filter(f => f.id !== id);
    return withDelay({ success: true });
  }
};
