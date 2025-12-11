import requests

url = "https://exercisedb.p.rapidapi.com/exercises/targetList"

headers = {
	"x-rapidapi-key": "912585a3afmshb323f8c863de68bp1ab1fbjsn75a20ef76d1d",
	"x-rapidapi-host": "exercisedb.p.rapidapi.com"
}

response = requests.get(url, headers=headers)
targets = response.json()