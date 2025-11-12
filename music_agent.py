import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import random
from dotenv import load_dotenv
from langchain import hub
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_structured_chat_agent
import agentops
from agentops.langchain_callback_handler import LangchainCallbackHandler as AgentOpsLangchainCallbackHandler
from typing import List, Dict, Any, Optional

load_dotenv()

client_id: str = os.environ.get('Spotify_Client', '')
client_secret: str = os.environ.get('Spotify_Secret', '')

agent_ops_keys: str = os.environ.get('AGENT_OPS_KEY', '')

if not client_id or not client_secret:
    raise ValueError("Spotify_Client or Spotify_Secret environment variables are not set. "
                     "Please ensure they are defined in your .env file or environment.")
spotify_client: spotipy.Spotify = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
)

agentops_handler: Optional[AgentOpsLangchainCallbackHandler] = None
if agent_ops_keys:
    agentops.init(api_key=agent_ops_keys)
    agentops_handler = AgentOpsLangchainCallbackHandler(api_key=agent_ops_keys, tags=[' New Music Agent'])
else:
    print("Warning: AGENT_OPS_KEY environment variable not set. AgentOps monitoring will be disabled.")

SPOTIFY_TOP_TRACKS_LIMIT: int = 10

def retrieve_artist_id(artist_name: str) -> str:
    results: Dict[str, Any] = spotify_client.search(q='artist:' + artist_name, type='artist')
    items: List[Dict[str, Any]] = results['artists']['items']
    if not items:
        raise ValueError(f"No artist found with name {artist_name}")
    return items[0]['id']

def retrieve_tracks(artist_id: str, num_tracks: int) -> List[str]:
    top_tracks: Dict[str, Any] = spotify_client.artist_top_tracks(artist_id)
    return [track['name'] for track in top_tracks['tracks'][:num_tracks]]

@tool
def get_music_recommendations(artists: List[str], tracks: int) -> List[str]:
    final_tracks: List[str] = []
    for artist in artists:
        try:
            artist_id: str = retrieve_artist_id(artist)
            artist_tracks: List[str] = retrieve_tracks(artist_id, SPOTIFY_TOP_TRACKS_LIMIT)
            final_tracks.extend(artist_tracks)
        except ValueError as e:
            print(f"Skipping artist '{artist}' due to error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for artist '{artist}': {e}")
    
    random.shuffle(final_tracks)
    return final_tracks[:tracks]

def run_music_agent(input_query: str) -> Dict[str, Any]:
    llm_callbacks: List[Any] = []
    if agentops_handler:
        llm_callbacks.append(agentops_handler)

    llm = ChatOpenAI(temperature=0.0, callbacks=llm_callbacks)
    
    tools = [get_music_recommendations]

    prompt = hub.pull("hwchase17/structured-chat-agent")

    agent = create_structured_chat_agent(llm, tools, prompt)

    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    input_data: Dict[str, str] = {"input": input_query}
    response: Dict[str, Any] = executor.invoke(input_data)
    
    return response

if __name__ == "__main__":
    try:
        input_query_example: str = "I like the following artists: Drake, Future. Can I get 5 song recommendations?"
        print(f"--- Running Music Agent with query: '{input_query_example}' ---")
        
        agent_response = run_music_agent(input_query_example)
        
        print("\n--- Agent Final Response ---")
        print(agent_response)

        if agent_ops_keys:
            agentops.end_session('Success')
        
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
        if agent_ops_keys:
            agentops.end_session('Failure', reason=f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred during agent execution: {e}")
        if agent_ops_keys:
            agentops.end_session('Failure', reason=f"Unexpected Error: {e}")