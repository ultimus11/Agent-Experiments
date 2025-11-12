import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import random
import asyncio
import agentops
from dotenv import load_dotenv
from langchain import hub
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_structured_chat_agent
from agentops import init, end_session
from agentops.langchain_callback_handler import AsyncLangchainCallbackHandler as AgentOpsAsyncLangchainCallbackHandler

load_dotenv()

client_id: str = os.environ['Spotify_Client']
client_secret: str = os.environ['Spotify_Secret']

agent_ops_keys: str = os.environ['AGENT_OPS_KEY']

spotify_client = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

def retrieve_artist_id(artist_name: str) -> str:
    results = spotify_client.search(q='artist:' + artist_name, type='artist')
    items = results['artists']['items']
    if not items:
        raise ValueError(f"No artist found with name '{artist_name}'")
    return items[0]['id']

def retrieve_tracks(artist_id: str, num_tracks: int) -> list[str]:
    top_tracks = spotify_client.artist_top_tracks(artist_id)
    if not top_tracks or 'tracks' not in top_tracks or not top_tracks['tracks']:
        return []
    return [track['name'] for track in top_tracks['tracks'][:num_tracks]]

@tool
def get_music_recommendations(artists: list[str], tracks: int) -> list[str]:
    final_tracks: list[str] = []
    for artist in artists:
        try:
            artist_id = retrieve_artist_id(artist)
            artist_tracks = retrieve_tracks(artist_id, min(tracks, 10))
            final_tracks.extend(artist_tracks)
        except ValueError as e:
            print(f"Error retrieving recommendations for artist '{artist}': {e}")
            continue
    random.shuffle(final_tracks)
    return final_tracks

agentops_handler = AgentOpsAsyncLangchainCallbackHandler(api_key=agent_ops_keys, tags=[' New Music Agent Async'])
agentops.init(api_key=agent_ops_keys)

llm = ChatOpenAI(temperature=0.0, callbacks=[agentops_handler])
tools = [get_music_recommendations]

prompt = hub.pull("hwchase17/structured-chat-agent")

agent = create_structured_chat_agent(llm, tools, prompt)

executor = AgentExecutor(agent=agent, tools=tools, verbose=True, callbacks=[agentops_handler])

async def main():
    try:
        input_data = {"input": "I like the following artists: Drake, Future. Can I get 5 song recommendations?"}
        response = await executor.ainvoke(input_data)
        print(response)
    finally:
        agentops.end_session('Success')

if __name__ == '__main__':
    asyncio.run(main())