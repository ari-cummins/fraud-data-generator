FIRST_NAMES = [
    "Oliver", "Charlotte", "William", "Amelia", "Jack", "Isla", "Noah", "Mia",
    "Thomas", "Grace", "James", "Ava", "Lucas", "Chloe", "Henry", "Sophie",
    "Ethan", "Zoe", "Liam", "Ruby", "Alexander", "Evie", "Samuel", "Harper",
    "Benjamin", "Willow", "Hugo", "Ella", "Archie", "Matilda", "Leo", "Poppy",
    "Aarav", "Priya", "Wei", "Mei", "Mohammed", "Fatima", "Dimitri", "Elena",
    "Sione", "Aroha", "Tomas", "Bianca", "Nikolas", "Yasmin", "Rohan", "Anika",
    "Callum", "Freya", "Declan", "Imogen", "Jarrah", "Kirra", "Marcus", "Nadia",
    "Patrick", "Rosie", "Sebastian", "Talia", "Vincent", "Wren", "Xavier", "Yara",
]

LAST_NAMES = [
    "Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Nguyen", "Martin",
    "Anderson", "Thompson", "Walker", "Ryan", "Robinson", "Kelly", "White", "Lee",
    "Harris", "Chen", "Young", "Patel", "Singh", "Wang", "Ali", "Kaur",
    "Mitchell", "Campbell", "Stewart", "Murphy", "O'Brien", "Bennett", "Hughes", "Ellis",
    "Fletcher", "Gallagher", "Hayes", "Ingram", "Jenkins", "Kowalski", "Lambert", "Moss",
    "Novak", "Osborne", "Pritchard", "Quinn", "Rasmussen", "Sutherland", "Tran", "Underwood",
    "Vasquez", "Whitfield", "Yilmaz", "Zammit", "Abbott", "Barlow", "Chidiac", "Delaney",
]

STREETS = [
    "Anzac Pde", "Botany Rd", "Canberra Ave", "Darling St", "Elizabeth St", "Flinders Ln",
    "George St", "Hargrave St", "Ipswich Rd", "Johnston St", "King William St", "Latrobe St",
    "Macquarie St", "Northbourne Ave", "Oxford St", "Parramatta Rd", "Queen St", "Rundle Mall",
    "Sturt St", "Toorak Rd", "Unley Rd", "Victoria Pde", "Wellington St", "York St",
    "Beaufort St", "Chapel St", "Doncaster Rd", "Eagle St", "Franklin St", "Glenferrie Rd",
]

SUBURBS = [
    ("Braddon", "ACT", "2612"), ("Belconnen", "ACT", "2617"), ("Woden", "ACT", "2606"),
    ("Newtown", "NSW", "2042"), ("Parramatta", "NSW", "2150"), ("Chatswood", "NSW", "2067"),
    ("Fitzroy", "VIC", "3065"), ("Footscray", "VIC", "3011"), ("Box Hill", "VIC", "3128"),
    ("Fortitude Valley", "QLD", "4006"), ("Toowong", "QLD", "4066"), ("Southport", "QLD", "4215"),
    ("Fremantle", "WA", "6160"), ("Joondalup", "WA", "6027"), ("Norwood", "SA", "5067"),
    ("Prospect", "SA", "5082"), ("Sandy Bay", "TAS", "7005"), ("Alice Springs", "NT", "0870"),
    ("Newcastle", "NSW", "2300"), ("Geelong", "VIC", "3220"), ("Cairns", "QLD", "4870"),
]

TEAMS = ["Identity Services", "Registrations", "Renewals", "Permits", "Compliance", "Customer Care"]
ROLES = ["Officer", "Senior Officer", "Team Leader", "Supervisor"]
ACCESS_LEVELS = ["standard", "senior", "admin"]
SITES = ["Canberra", "Sydney", "Melbourne", "Brisbane", "Perth"]

QUEUES = ["Identity", "Registrations", "Renewals", "Permits", "General"]
DISPOSITIONS = ["resolved", "escalated", "callback_scheduled", "referred_to_specialist", "abandoned"]
IVR_PATHS = ["main>identity", "main>registrations", "main>renewals", "main>permits", "main>general"]

PROFILE_FIELDS = ["residential_address", "postal_address", "mobile_phone", "email",
                  "identity_document", "bank_account", "preferred_name"]

FIELD_GROUPS = {  # which CRM screens an access touched
    "profile": ["given_name", "family_name", "date_of_birth"],
    "contact": ["residential_address", "mobile_phone", "email"],
    "identity": ["identity_document", "document_number", "issue_date"],
    "financial": ["bank_account", "payment_history"],
    "linked": ["linked_customer", "household_members"],
}

USER_AGENTS = ["Chrome/Windows", "Safari/iOS", "Chrome/Android", "Edge/Windows", "Safari/macOS"]