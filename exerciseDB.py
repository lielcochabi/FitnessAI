import requests
import urllib.parse
headers = {
	"x-rapidapi-key": "912585a3afmshb323f8c863de68bp1ab1fbjsn75a20ef76d1d",
	"x-rapidapi-host": "exercisedb.p.rapidapi.com"
}
body_parts = ["back","cardio","chest","lower arms","lower legs","neck","shoulders","upper arms","upper legs","waist"]
muscles = ["abductors","abs","adductors","biceps","calves","cardiovascular system","delts","forearms","glutes","hamstrings","lats","levator scapulae","pectorals","quads","serratus anterior","spine","traps","triceps","upper back"]

def get_body_parts():
	return body_parts

def get_muscles():
	return muscles

def get_exercises_by_bodypart(bodypart: str):
	# Normalize input: lowercase + URL encoding
    bodypart_clean = urllib.parse.quote(bodypart.lower())

    url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{bodypart_clean}"

    try:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        return response.json()   # returns list of exercises (each exercise = dict)
    except Exception as e:
        print(f"Error fetching exercises for {bodypart}:", e)
        return []
