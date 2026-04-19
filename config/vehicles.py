# =========================================================
# vehicles.py
# Supported vehicle search space by make/model/year range.
#
# Notes:
# - Vehicle year ranges are authoritative for each make/model.
# - We do this because the overall search range may be wider than the production year range of certain models. 
# - Runtime config can further narrow the active search years,
#   but it should never expand beyond these bounds.
# =========================================================


SUPPORTED_VEHICLES = [
    {"year_range": (2012, 2020), "make": "Ford", "model": "F-150"},
    {"year_range": (2012, 2020), "make": "Chevrolet", "model": "Silverado 1500"},
    {"year_range": (2012, 2020), "make": "Ram", "model": "1500"},
    {"year_range": (2012, 2020), "make": "Toyota", "model": "Camry"},
    {"year_range": (2012, 2020), "make": "Honda", "model": "Accord"},
    {"year_range": (2012, 2020), "make": "Toyota", "model": "Corolla"},
    {"year_range": (2012, 2020), "make": "Honda", "model": "Civic"},
    {"year_range": (2012, 2020), "make": "Toyota", "model": "RAV4"},
    {"year_range": (2012, 2020), "make": "Honda", "model": "CR-V"},
    {"year_range": (2012, 2020), "make": "Nissan", "model": "Rogue"},
]

# -- Aliases for normalizing make/model names from raw text --
MAKE_ALIASES = {
    "chevy": "Chevrolet",
    "chevrolet": "Chevrolet",
    "ford": "Ford",
    "honda": "Honda",
    "toyota": "Toyota",
    "nissan": "Nissan",
    "ram": "Ram",
    "dodge ram": "Ram",
}

# -- These are used to normalize model names during cleansing, since many listings use informal or shorthand model references.
MODEL_ALIASES = {
    "f150": "F-150",
    "f-150": "F-150",
    "silverado": "Silverado 1500",
    "silverado 1500": "Silverado 1500",
    "ram 1500": "1500",
    "dodge ram 1500": "1500",
    "accord": "Accord",
    "camry": "Camry",
    "corolla": "Corolla",
    "civic": "Civic",
    "rav4": "RAV4",
    "crv": "CR-V",
    "cr-v": "CR-V",
    "rogue": "Rogue",
}

# -- These are used to exclude heavy duty variants of supported models.
HEAVY_DUTY_EXCLUSIONS = {
    "Ford": ["f-250", "f250", "f-350", "f350", "super duty"],
    "Chevrolet": ["2500hd", "3500hd", "silverado 2500", "silverado 3500"],
    "Ram": ["2500", "3500", "4500", "5500"],
}