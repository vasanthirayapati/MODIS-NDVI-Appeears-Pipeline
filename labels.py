# STATE BOUNDARIES + LABELS 

# Manual wrapping for selected states only
STATE_LABEL_WRAP = {
    "Andhra Pradesh": "Andhra\nPradesh",
    "Jammu & Kashmir": "Jammu &\nKashmir",
    "Dadra & Nagar Haveli": "Dadra &\nNagar \nHaveli",
    "Himachal Pradesh": "Himachal\nPradesh",
    "Andaman & Nicobar Islands": "Andaman &\nNicobar Islands",
    "West Bengal": "West\nBengal"
}

# Manual offsets for fine adjustment (lon, lat)
STATE_LABEL_OFFSETS = {
    "Kerala": (0.6, -0.5),
    "Tripura": (0, 0.1),
    "Mizoram":(0,-0.6),
    "Manipur": (0.4, 0),
    "Meghalaya":(0,-0.1),
    "Arunachal Pradesh": (0.2,0.2),
    "Andhra Pradesh": (-1.3,-0.9),
    "Karnataka": (-0.55,-0.3),
    "Jharkhand":(-0.2,0.2),
    "West Bengal": (-0.3,-0.8),
    "Assam":(-1,0),
    "Nagaland": (0,-0.2),
    "Punjab": (-0.6,-0.6),
    "Haryana": (0,0.1),
    "Nagaland": (0, 0),
    "Dadra & Nagar Haveli": (0.5, -0.3),
    "Andaman & Nicobar Islands": (0.8, -1.8),
    "Daman & Diu": (-1.2,0),
    
    
}


# DISTRICT BOUNDARIES + LABELS

# Define manual wrap and shift inside the function
DISTRICT_LABEL_WRAP = {
    #Chhattisgarh
    "Uttar Bastar Kanker" : "Uttar\nBastar\nKanker",  
    "Dakshin Bastar Dantewada": "Dakshin\nBastar\nDantewada",   
    "Janjgir - Champa": "Janjgir\nChampa",

    #Rajasthan
    "Sawai Madhopur": "Sawai\nMadhopur",

    #Madhya Pradesh
    "Agar Malwa": "Agar\nMalwa",

    #Uttar Pradesh
    "Gautam Buddha Nagar":"Gautam\nBuddha\nNagar",
    "Kanpur Dehat":"Kanpur\nDehat",
    "Kanpur Nagar":"Kanpur\nNagar",
    "Sant Kabir Nagar":"Sant\nKabir\nNagar",
    "Ambedkar Nagar":"Ambedkar\nNagar",
    "Bara Banki":"Bara\nBanki",

    #Andhra Pradesh
    "Sri Potti Sriramulu Nel": "Sri Potti\nSriramulu\nNellore",
    "West Godavari": "West\nGodavari",
    "East Godavari": "East\nGodavari",

    #Meghalaya
    "South West Garo Hills": "South West\nGaro Hills",
    "South West Khasi Hills":"South West\nKhasi Hills",
    "West Garo Hills": "West Garo\nHills",

    #Karnataka
    "Uttara Kannada": "Uttara\nKannada",
    "Dakshina Kannada":"Dakshina\nKannada",
    "Bengaluru Rural": "Bengaluru\nRural",

    #Maharashtra 
    "Mumbai Suburban": "Mumbai\nSuburban",

    #West Bengal
    "Dinajpur Dakshin": "Dinajpur\nDakshin",
    "Medinipur West": "Medinipur\nWest",
    "Paschim Bardhaman": "Paschim\nBardhaman",
    "Purba Bardhaman" : " Purba\nBardhaman",
    "South Twenty Four Pargan*" : "South\nTwent\nFour\nPargan*",
    "Purba Medinipur": "Purba\nMedinipur",
    "Uttar Dinajpur": "Uttar\nDinajpur",
    "Cooch Behar": "Cooch\nBehar",
    "24 Paraganas North": "24\nParaganas\nNorth",
    "24 Paraganas South":"24 Paraganas\nSouth",
}

DISTRICT_LABEL_SHIFT = {
    #Jammu and Kashmir
    "Muzaffarabad": (0,-0.2),

    #Haryana
    "Yamunanagar": (-0.15,0),
    "Kurukshetra": (0,-0.05),
    "Gurugram": (0,0.05),
    "Faridabad": (-0.05,0),
    "Mahendragarh" : (0.15,0.2),

    #Madhya Pradesh 
    "Neemuch": (0,-0.1),
    "Niwari": (0.17,-0.15),
    "Alirajpur": (0.09,-0.02),
    "Burhanpur": (0,0.1),
    "Tikamgarh": (0.03,0.05),
    "Anuppur": (0.15,-0.1),
    "Ratlam": (0,-0.08),
    "Shahdol": (0.22,-0.3),
    "Agar Malwa": (0.1,-0.15),
    "Datia": (-0.02,-0.05),
    "Sehore": (0,-0.1),

    
    #Chhattisgarh
    "Balrampur": (-0.17,0),
    "Raigarh":(-0.05,0.1),
    "Raipur":(0,0.1),
    "Koriya":(0,0.2),
    "Bilaspur": (0.2,-0.2),
    "Mungeli" :(0.15,0.2),
    "Kabeerdham" :(0.1,-0.2),
    "Mahasamund": (0,0.05),
    "Rajnandgaon": (0.2,0.05),
    "Uttar Bastar Kanker":(0,0),
    "Gariaband":(-0.2,-0.05),
    "Kondagaon":(-0.1,0.05),
    "Narayanpur":(0.15,0),
    "Dakshin Bastar Dantewada":(0,0),
    "Sukma":(-0.05,-0.2),

    #Rajasthan
    "Ganganagar":(0.2,0.1),
    "Hanumangarh":(0,-0.2),
    "Churu":(0,0.2),
    "Bharatpur":(-0.2,0),
    "Dhaulpur":(-0.13,0),
    "Karauli":(-0.1,-0.2),
    "Sawai Madhopur":(0,0),
    "Baran": (0,0.25),
    "Jhalawar":(-0.2,0.15),
    "Banswara":(-0.1,0.08),
    "Dungarpur":(0.1,0.15),
    "Pratapgarh":(-0.17,0),
    "Chittaurgarh":(-0.1,0),
    "Tonk":(0,0.05),

    #Uttar Pradesh
    "Saharanpur":(0,-0.2),
    "Shamli":(0.1,-0.1),
    "Muzaffarnagar":(0.15,0.1),
    "Baghpat":(0.2,0.1),
    "Moradabad":(0,0.1),
    "Gautam Buddha Nagar":(0.4,-0.15),
    "Ghaziabad":(0.2,0.05),
    "Mathura":(0.09,0.11),
    "Mainpuri":(0,-0.1),
    "Agra":(0.1,0),
    "Bulandshahr":(-0.1,0.125),
    "Hapur":(0,-0.05),
    "Amroha":(0.13,0),
    "Sambhal":(0.2,0),
    "Etawah":(0,0.16),
    "Kanpur Dehat":(0,-0.1),
    "Amethi":(0,0.1),
    "Firozabad":(0,0.1),
    "Kanpur Nagar":(0.1,-0.2),
    "Jhansi":(0.45,0.15),
    "Lalitpur":(0.1,-0.2),
    "Sonbhadra":(0.04,0.2),
    "Chandauli":(-0.3,0),
    "Varanasi":(0.2,0),
    "Bhadohi":(-0.1,0),
    "Prayagraj":(0,-0.06),
    "Chitrakoot":(0,0.06),
    "Deoria":(0.12,-0.1),
    "Kushinagar":(0.05,-0.2),
    "Mahrajganj":(0,-0.1),
    "Shrawasti":(-0.1,0.1),
    "Siddharthnagar":(-0.3,0),
    "Gorakhpur":(0.15,-0.2),
    "Sant Kabir Nagar":(0.1,0.07),
    "Bahraich":(0.2,-0.3),
    "Balrampur":(0,0.05),
    "Mau":(0.1,0),
    "Pratapgarh":(-0.1,-0.04),
    "Jaunpur":(0.1,-0.1),
    "Bara Banki":(0,0),
    "Gonda":(0,-0.1),
    "Sultanpur":(0,-0.1),
    "Hardoi":(0,-0.1),
    "Lucknow":(0,-0.1),

    #Tamil Nadu
    "Ramanathapuram": (-0.18, -0.2),
    "Thoothukkudi": (-0.1,0.2),
    "Thiruvarur": (0, 0.1),
    "Coimbatore": (0,0.2),
    "Karur": (-0.40, 0.1),
    "Nagapattinam":(-0.23, -0.2),
    "Kanniyakumari":(0.2,0),
    "Chennai":(-0.2,0),
    "Kancheepuram":(-0.15,0),
    "The Nilgiris": (0.15,0),
    "Viluppuram": (-0.05,-0.15),
    "Puducherry":(-0.24,0),
    "Karaikal":(-0.18,-0.03),


    #Andhra Pradesh 
    "East Godavari": (0,0.2),
    "Vizianagaram":(0.2,-0.1),

    #Karnataka
    "Davanagere": (0, 0.2),
    "Dharwad": (0,-0.1),
    "Uttara Kannada": (0,0.15),
    "Udupi":(0.05,0),
    "Chikkaballapura":(-0.2,0),
    "Chitradurga":(-0.1,-0.1),
    "Kodagu":(0.1,0),
    "Ramanagara":(-0.1,0.05),
    "Dakshina Kannada":(0,0.1),
    "Chamarajanagara":(-0.1,0),

    #Meghalaya 
    "West Garo Hills":(0,0.1),
    "West Jaintia Hills":(0.06,0.1),

    #Odisha
    "Sundargarh":(0,0.1),
    "Nuapada":(0.15,0),
    "Nabarangapur":(0.15,0),
    "Puri":(0.3,0.1),
    "Jagatsinghapur":(-0.15,0.1),
    "Baleshwar":(-0.15,0),
    "Kendrapara":(-0.1,0),
    "Jajapur":(-0.04,0),
    "Balangir":(0,0.05),
    

    #Maharashtra
    "Gondiya":(-0.1,0.1),
    "Mumbai": (0.3,-0.1),
    "Mumbai Suburban": (0.28,0),
    "Sindhudurg":(0.25,0),
    "Nandurbar":(-0.3,0.2),
    "Ratnagiri":(0.1,0),
    "Raigarh":(0.1,0),
    "Kolhapur":(-0.2,0),
    "Bhandara": (0,-0.1),

    #West Bengal
    "Medinipur West": (0.05, 0.2),
    "Howrah": (0.02,0.04),
    "Hooghly": (0,-0.1),
    "North Twenty Four Pargan*" : (-0.05,0.2),
    "Birbhum" : (-0.05,-0.17),
    "Murshidabad" : (-0.1,-0.1),
    "Nadia" :(-0.07,0),
    "Dinajpur Dakshin":(0.03,-0.04),
    "Alipurduar":(0.0,0),
    "Cooch Behar": (-0.04,0),
    "Darjiling" :(0.17,0),
    "Kalimpong": (0,0.03),
    "Jhargram":(0,-0.1),
    "24 Paraganas North":(0,0.09),
}

