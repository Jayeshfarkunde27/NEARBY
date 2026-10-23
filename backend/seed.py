"""Seeds SIMULATED verified hosts near Pimpri-Chinchwad. Disclose them as simulated.
Run: GOOGLE_APPLICATION_CREDENTIALS=key.json python seed.py"""
import firebase_admin, random
from firebase_admin import firestore
firebase_admin.initialize_app(); db = firestore.client(); random.seed(7)
NAMES = ["Sai Tea Stall","Patil Residence","Green Park Parking","Om Medical Store","Kulkarni Villa",
         "Chai Point Annex","Shree Garage","Hotel Sneha","Joshi Bungalow","City Mart Parking","Maruti Dhaba","Rane Residence"]
for n in NAMES:
    db.collection("hosts").add({"name": n, "lat": round(18.6298 + random.uniform(-.08, .08), 3),
        "lng": round(73.7997 + random.uniform(-.08, .08), 3), "kw": random.choice([2.2, 3.3, 7.4, 11]),
        "connectors": random.sample(["socket15A","type2","ccs2"], k=2),
        "amenities": random.sample(["seating","tea","restroom","shade","food"], k=3),
        "available": True, "status": "verified", "trust_rating": round(random.uniform(3.6, 4.9), 1), "simulated": True})
print("seeded", len(NAMES))
