from flask import Flask, render_template, request, jsonify, abort
from scraper import OtakudesuScraper

app = Flask(__name__)
scraper = OtakudesuScraper()

@app.route('/')
def index():
    data = scraper.get_home()
    return render_template('home.html', ongoing=data['ongoing'], complete=data['complete'])

@app.route('/ongoing')
def ongoing():
    page = request.args.get('page', 1, type=int)
    anime_list = scraper.get_ongoing_anime(page)
    return render_template('ongoing.html', anime_list=anime_list, page=page)

@app.route('/list')
def anime_list():
    anime_list = scraper.get_anime_list()
    return render_template('anime_list.html', anime_list=anime_list)

@app.route('/genre')
def genre_list():
    genres = scraper.get_genre_list()
    return render_template('genre_list.html', genres=genres)

@app.route('/search')
def search():
    query = request.args.get('s', '')
    if not query:
        return render_template('search_results.html', results=[], query="")
    results = scraper.search_anime(query)
    return render_template('search_results.html', results=results, query=query)

@app.route('/anime/<slug>')
def anime_detail(slug):
    details = scraper.get_anime_details(slug)
    if not details:
        abort(404)
    return render_template('anime_detail.html', anime=details)

@app.route('/episode/<slug>')
def episode_detail(slug):
    details = scraper.get_episode_details(slug)
    if not details:
        abort(404)
    return render_template('episode.html', episode=details)

@app.route('/api/resolve', methods=['POST'])
def resolve_api():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    stream_url = None

    # Check if we are resolving a mirror payload (from data-content)
    if 'data_content' in data:
        stream_url = scraper.resolve_stream(data['data_content'])

    # Check if we are extracting from a URL (e.g. desustream iframe src)
    elif 'url' in data:
        url = data['url']
        if "desustream" in url:
            stream_url = scraper.extract_video_from_desustream(url)
        else:
            stream_url = url # Just return if we can't extract deeper

    if stream_url:
        return jsonify({"url": stream_url})
    return jsonify({"error": "Could not resolve stream"}), 404

if __name__ == '__main__':
    # Disable debug mode for security in production-like environment
    app.run(debug=False, host='0.0.0.0', port=5000)
