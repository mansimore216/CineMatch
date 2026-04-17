# ============================================================
# app.py - Flask Backend for Movie Recommender (FINAL VERSION)
# ============================================================

from flask import Flask, request, jsonify, render_template
import pickle
import requests
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# INIT
# ============================================================

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# TMDB API KEY
TMDB_API_KEY = "ded1412e973c9577d5504d7e367acce2"

# Default poster
DEFAULT_POSTER = "https://via.placeholder.com/500x750/1a1a2e/e94560?text=No+Poster"

# ============================================================
# LOAD DATA
# ============================================================

movies = pickle.load(open("movies.pkl", "rb"))
similarity = pickle.load(open("similarity.pkl", "rb"))

# ============================================================
# POSTER CACHE + FETCH FUNCTION
# ============================================================

poster_cache = {}

def fetch_poster(movie_id):
    try:
        url = "https://api.themoviedb.org/3/movie/{}?api_key={}&language=en-US".format(
            movie_id, TMDB_API_KEY
        )

        response = requests.get(url, timeout=3)

        if response.status_code != 200:
            print("TMDB ERROR:", response.status_code)
            return DEFAULT_POSTER

        data = response.json()

        poster_path = data.get("poster_path")

        if poster_path and poster_path != "":
            return "https://image.tmdb.org/t/p/w500" + poster_path

        return DEFAULT_POSTER

    except Exception as e:
        print("Poster error:", e)
        return DEFAULT_POSTER

# ============================================================
# RECOMMEND FUNCTION
# ============================================================

def recommend(movie_name):
    # Case-insensitive match
    movie_list = movies[movies["title"].str.lower() == movie_name.lower()]

    if movie_list.empty:
        return [], []

    movie_index = movie_list.index[0]
    distances = similarity[movie_index]

    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]

    recommended_movies = []
    movie_ids = []

    for i in movies_list:
        idx = i[0]
        recommended_movies.append(movies.iloc[idx].title)
        movie_ids.append(movies.iloc[idx].movie_id)
    print("DEBUG movie_id:", movie_ids)

    # 🔥 Parallel API calls (FAST)
    with ThreadPoolExecutor(max_workers=5) as executor:
        posters = list(executor.map(fetch_poster, movie_ids))

    return recommended_movies, posters

# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    movie_titles = sorted(movies["title"].tolist())
    return render_template("index.html", movies=movie_titles)

@app.route("/recommend", methods=["POST"])
def recommend_movies():
    data = request.get_json()

    if not data or "movie" not in data:
        return jsonify({"error": "No movie provided"}), 400

    selected_movie = data["movie"].strip()

    names, posters = recommend(selected_movie)

    if not names:
        return jsonify({"error": f"Movie '{selected_movie}' not found"}), 404

    return jsonify({
        "movies": names,
        "posters": posters
    })

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, port=5001)