import os
import openai


openai.api_key = os.getenv('OPENAI_API_KEY')


def generate_summary(transcript: str, mode: str = 'meeting') -> str:
prompt = f"Resuma o texto abaixo gerando:\n- Principais pontos\n- Decisões\n- Ações com responsáveis\n\nTranscrição:\n{transcript}\n"
# Use o endpoint de Chat Completions / Responses dependendo do SDK
response = openai.ChatCompletion.create(
model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
messages=[{"role": "user", "content": prompt}],
max_tokens=800,
)
return response['choices'][0]['message']['content']