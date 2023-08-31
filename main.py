import json
import csv
import math

import quart
import quart_cors
from quart import Quart, request, jsonify

class Airport:
    def __init__(self, row):
        self.name = row["name"]
        self.ident = row["ident"]
        self.type = row["type"]
        self.latitude_deg = float(row["latitude_deg"])
        self.longitude_deg = float(row["longitude_deg"])
        self.wikipedia_link = row["wikipedia_link"]

    def to_json(self):
        return {
            'name': self.name,
            'ident': self.ident,
            'type': self.type,
            'lat': self.latitude_deg,
            'long': self.longitude_deg,
            'url': self.wikipedia_link
        }

def load_airports_from_csv(file):
    airports = []

    with open(file, 'r', encoding="utf8") as csv_file:
        csv_reader = csv.DictReader(csv_file)

        for row in csv_reader:
            airports.append(Airport(row))

    return airports

airports = load_airports_from_csv("data/airports.csv")

def filter_type_airports(filtered_type):
    return [a for a in airports if a.type is None or (a.type and filtered_type in a.type)]

def find_nearest_airports(lat, long, count, type):
    return sorted(filter_type_airports(type), key=lambda a: (math.sqrt((a.latitude_deg - lat)**2 + (a.longitude_deg - long)**2)))[:count]

def search_airports_by_name(city_name):
    return [a for a in airports if city_name.lower() in a.name.lower()]

def search_airports_by_ident(ident):
    return [a for a in airports if ident.lower() in a.ident.lower()]

def generate_flight_plan_link(coordinates):
    # Convert the coordinates to the format expected by the SkyVector URL
    formatted_coords = []
    for coord in coordinates:
        lat = coord["lat"]
        long = coord["long"]

        # Convert decimal latitude to degrees, minutes, and seconds
        lat_degrees = abs(int(lat))
        lat_minutes_decimal = (abs(lat) - lat_degrees) * 60
        lat_minutes = int(lat_minutes_decimal)
        lat_seconds = round((lat_minutes_decimal - lat_minutes) * 60)
        lat_formatted = "{:02d}{:02d}{:02d}".format(lat_degrees, lat_minutes, lat_seconds)

        # Convert decimal longitude to degrees, minutes, and seconds
        long_degrees = abs(int(long))
        long_minutes_decimal = (abs(long) - long_degrees) * 60
        long_minutes = int(long_minutes_decimal)
        long_seconds = round((long_minutes_decimal - long_minutes) * 60)
        long_formatted = "{:03d}{:02d}{:02d}".format(long_degrees, long_minutes, long_seconds)

        # Determine the direction for latitude (N or S) based on the sign of the value
        lat_dir = "N" if lat >= 0 else "S"
        # Determine the direction for longitude (E or W) based on the sign of the value
        long_dir = "E" if long >= 0 else "W"

        # Combine degrees, minutes, seconds, and direction to form the final coordinate string
        formatted_coords.append("{}{}{}{}".format(lat_formatted, lat_dir, long_formatted, long_dir))

    formatted_coords_str = "%20".join(formatted_coords)

    # Generate the SkyVector URL with the formatted coordinates
    return "https://skyvector.com/?fpl={}".format(formatted_coords_str)

app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

@app.get("/nearestAirports/<float:lat>/<float:long>")
async def nearest_airports(lat, long):
    count = int(request.args.get("count", 5))
    airport_type = request.args.get("type", None)

    result = find_nearest_airports(lat, long, count, airport_type)

    return jsonify([r.to_json() for r in result])

@app.get("/searchByName/<string:city_name>")
async def search_by_name(city_name):
    result = search_airports_by_name(city_name)

    return jsonify([r.to_json() for r in result])

@app.get("/searchByIdent/<string:ident>")
async def search_by_ident(ident):
    result = search_airports_by_ident(ident)

    return jsonify([r.to_json() for r in result])

@app.post("/flightPlan")
async def flight_plan():
    try:
        # Parse the request body as JSON
        request_data = await request.get_json()

        # Validate that the 'coordinates' key is present in the request data
        if "coordinates" not in request_data:
            return {"error": "Invalid input provided. Missing coordinates."}, 400

        # Extract the coordinates from the request data
        coordinates = request_data["coordinates"]

        # Validate that the coordinates are an array
        if not isinstance(coordinates, list):
            return {"error": "Invalid input provided. Coordinates must be an array."}, 400

        # Generate the flight plan link based on the coordinates
        flight_plan_link = generate_flight_plan_link(coordinates)

        # Return the flight plan link as a JSON response
        return {"flightPlanLink": flight_plan_link}

    except json.JSONDecodeError:
        # Handle JSON parsing errors
        return {"error": "Invalid JSON input provided."}, 400

@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("./.well-known/ai-plugin.json") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/json")

@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")

def main():
    app.run(debug=True, host="0.0.0.0", port=5003)

if __name__ == "__main__":
    main()
