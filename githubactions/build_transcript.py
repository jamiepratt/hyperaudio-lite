

import urllib.parse

import requests

import json

import os

import unicodedata
import re

import spacy

from googletrans import Translator

"""# Helper Functions"""

def render_template(template_path, context=None):
    if context is None:
        context = {}
    with open(template_path, 'r', encoding='utf-8') as file:
        template = file.read()
    
    for key, value in context.items():
        placeholder = '{{' + key + '}}'  # Adjust based on your placeholder format
        template = template.replace(placeholder, value)
    
    return template

def get_json_response (url):
  lingq_api_key = os.environ.get('LINGQ_API_KEY')
  if not lingq_api_key:
    raise ValueError("LINGQ_API_KEY is not set in the environment variables.")  
  headers = {
    'Authorization': f'Token {lingq_api_key}',
    'Content-Type': 'application/json'
  }
  response = requests.get(f'{url}?page_size=1000', headers=headers)
  return response.json()

def print_json (json_parsed):
  print (json.dumps(json_parsed, indent = 4))

def legal_filename(filename):
    # Convert to ASCII, removing non-ASCII characters
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode()
    
    # Replace remaining illegal characters with an underscore
    filename = re.sub(r'[^\w\-\. ]', '_', filename)
    
    # Remove leading and trailing whitespace, periods, and underscores
    filename = filename.strip(' ._')
    
    return filename


# Function to process text and return HTML with color-coded cases and tooltips
def process_paragraph(paragraph, attribute_string):
    doc = nlp(paragraph)
    highlighted_text = ""
    for token in doc:

      if token.pos_ == "PUNCT" :
        highlighted_text += token.text
      else :
        if not highlighted_text == "":
          highlighted_text += ' '
        # Retrieve morphological information
        case = token.morph.get("Case")
        morph = " ".join(f'{token.morph}'.split("|"))
        # Define the tooltip text
        tooltip_text = f"{token.lemma_} {token.pos_}"
        if morph:
            tooltip_text += f"<br> ({morph})"
        morph_features = f'{token.morph}'.split("|")
        morph_features = [morph_feature.replace("=", "_") for morph_feature in morph_features]
        morph_features.append(token.pos_)
        styling_class = " ".join(morph_features)

        # Append the token span with style and tooltip
        highlighted_text += f'<span {attribute_string} class="{styling_class}" data-tooltip="{tooltip_text}">{token.text}</span>'

    return highlighted_text


#@title Choose a language model
model = "pl_core_news_lg" #@param ["fi_core_news_lg", "de_core_news_lg", "en_core_web_lg", "nl_core_news_lg", "sv_core_news_lg", "da_core_news_lg", "pl_core_news_lg", "ru_core_news_lg", "uk_core_news_lg"]

nlp = spacy.load(model)

language_code = "pl"

to_translate = set()
# Create a dictionary of translations of paragraphs.
# This will be used to avoid translating the same paragraph multiple times and
# we are sending off the translations in bulk.
course_ids = [1646223, 289027, 1440209, 1646225, 902291, 627905]
courses = {}
lessons = {}
for course_id in course_ids:
  course = courses[course_id] = get_json_response(f'https://www.lingq.com/api/v2/{language_code}/collections/{course_id}')
  lessons[course_id] = {}
  for lesson_from_course in course['lessons']:
    lessons[course_id][lesson_from_course['id']] = get_json_response(f"https://www.lingq.com/api/v3/{language_code}/lessons/{lesson_from_course['id']}")
    for paragraph in lessons[course_id][lesson_from_course['id']]['tokenizedText']:
      p_text = ""
      for sentence in paragraph:
        p_text += sentence['text'] + " "
      to_translate.add(p_text)
translator = Translator()
translation_objs = translator.translate(list(to_translate), dest='en', src=language_code)
translated = {}
for translation_obj in translation_objs:
  translated[translation_obj.origin] = translation_obj.text


course_list_html = ""

for course_id, course in courses.items():
  no = 1
  players_html = ''
  for lesson in lessons[course_id].values():

    transcript = '';
    last_timestamp = 0;
 
    for paragraph in lesson['tokenizedText']:
      paragraph_text = ""
      text_to_translate = ""
      for sentence in paragraph:
        if sentence['timestamp'] and sentence['timestamp'][0]:
          timestamp_start = int(float(sentence['timestamp'][0]) * 1000)
          timestamp_end = int(float(sentence['timestamp'][1]) * 1000)
          duration = timestamp_end - timestamp_start
          last_timestamp = timestamp_end
        else:
          timestamp_start = last_timestamp
          duration = 0
        text_to_translate += sentence['text']+ " "
        attribute_string = f"data-m=\"{timestamp_start}\" data-d=\"{duration}\""
        text = process_paragraph(sentence['text'], attribute_string)
        paragraph_text += f"<span class=\"tk\" {attribute_string}>{text}</span>\n"
      transcript += f"""
<div class="cnt-trans">
    <p>{paragraph_text} <button class="tgl-trans">English</button></p>
    <div class="trans-cont">
        <p class="trans">{translated[text_to_translate]}</p>
    </div>
</div>
"""
    players_html += render_template('templates/multiplayer_player.html',
                              {'audio_url' : lesson['audioUrl'],
                              'title' : lesson['title'],
                              'reader_lesson_url' : f"https://www.lingq.com/en/learn/pl/web/reader/{lesson['id']}/",
                              'transcript' : transcript,
                              'no' : f"{no}"}) + "\n"
    no += 1


  initialise_players = ''
  for n in range(1, no):
    initialise_players += f"new HyperaudioLite(\"hypertranscript{n}\", \"hyperplayer{n}\", minimizedMode, autoScroll, doubleClick, webMonetization, playOnClick);\n"

  html = render_template('templates/multiplayer_body.html',
                              {'title' : course['title'],
                              'reader_course_url' : f"https://www.lingq.com/en/learn/pl/web/library/course/{course_id}/",
                              'course_description' : course['description'],
                              'players' : players_html,
                              'initialise_players' : initialise_players})

  filename = legal_filename(course['title'])
  course_list_html += f'<li><a href="{filename}.html">{course["title"]}</a></li>\n'
  with open(f"gh-pages/{filename}.html", "w", encoding="utf-8") as file:
    file.write(html)

index_html = render_template('templates/index.html',
                              {'course_list' : course_list_html})
with open(f"gh-pages/index.html", "w", encoding="utf-8") as file:
    file.write(index_html)