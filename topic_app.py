import streamlit as st
import requests
import zipfile 
import json
from time import sleep
import yaml
import pandas as pd

def retrieve_url_podcast(parameters,episode_id):
    url_episodes_endpoint = 'https://listen-api.listennotes.com/api/v2/episodes'
    headers = {
    'X-ListenAPI-Key': parameters["api_key_listennotes"],
    }
    url = f"{url_episodes_endpoint}/{episode_id}"
    response = requests.request('GET', url, headers=headers)
    print(response.json())
    data = response.json()
    audio_url = data['audio']
    return audio_url

def send_transc_request(headers,audio_url):
    transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
    transcript_request = {
            'audio_url': audio_url,
            'iab_categories': True
        }
    transcript_response = requests.post(transcript_endpoint, json=transcript_request, headers=headers)
    transcript_id = transcript_response.json()["id"]   
    return transcript_id 

def obtain_polling_response(headers,transcript_id):
    polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    polling_response = requests.get(polling_endpoint, headers=headers)
    i=0
    while polling_response.json()["status"] != 'completed':
        sleep(5)
        polling_response = requests.get(polling_endpoint, headers=headers)
    return polling_response


def save_files(polling_response):
    with open("transcript.txt", 'w') as f:
        f.write(polling_response.json()['text'])
        f.close()
    with open('only_topics.json', 'w') as f:
        topics = polling_response.json()['iab_categories_result']
        json.dump(topics, f, indent=4) 

def save_zip():
    list_files = ['transcript.txt','only_topics.json','barplot.html']
    with zipfile.ZipFile('final.zip', 'w') as zipF:
      for file in list_files:
         zipF.write(file, compress_type=zipfile.ZIP_DEFLATED)
      zipF.close()

def create_df_topics():
    f = open("only_topics.json", "rb")
    topics = json.load(f)
    f.close()

    summary = topics["summary"]

    df = pd.DataFrame({})
    for k in summary:
        df1 = pd.DataFrame({'Topics':[k],'Probability':[summary[k]]})
        df = pd.concat([df,df1],ignore_index=True) 
    return df



# title of web app

st.markdown('# **Web App for Topic Modeling**')
bar = st.progress(0)

st.sidebar.header('Input parameter')

with st.sidebar.form(key='my_form'):
    episode_id = st.text_input('Insert Episode ID:')
    #7b23aaaaf1344501bdbe97141d5250ff
    submit_button = st.form_submit_button(label='Submit')

if submit_button:
    f = open('secrets.yaml','rb')
    parameters = yaml.load(f, Loader=yaml.FullLoader)
    f.close()
    # step 1 - Extract episode's url from listen notes
    audio_url = retrieve_url_podcast(parameters,episode_id)
    #bar.progress(30)
    api_key = parameters["api_key"]
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }

    # step 2 - retrieve id of transcription response from AssemblyAI
    transcript_id = send_transc_request(headers,audio_url)
    #bar.progress(70)

    # step 3 - topics
    polling_response = obtain_polling_response(headers,transcript_id)
    save_files(polling_response)
    df = create_df_topics()

    import plotly.express as px
    

    st.subheader("Top 5 topics extracted from the podcast's episode")
    fig = px.bar(df.iloc[:5,:].sort_values(by=['Probability'],ascending=True), x='Probability', y='Topics',text='Probability')
    fig.update_traces(texttemplate='%{text:.2f}', textposition="outside")
    fig.write_html("barplot.html")
    st.plotly_chart(fig)

    save_zip()

    with open("final.zip", "rb") as zip_download:
        btn = st.download_button(
            label="Download",
            data=zip_download,
            file_name="final.zip",
            mime="application/zip"
        )

    
    

