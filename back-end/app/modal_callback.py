# (Opcional) helpers específicos para lidar com o callback do Modal
# por exemplo, salvar resultado em banco e notificar usuário via websocket


from app.utils import save_result_to_storage


async def handle_modal_result(payload: dict):
file_id = payload.get('file_id')
transcript = payload.get('transcript')
# salvar e processar
save_result_to_storage(file_id, payload)


# opcional: chamar summarizer
# from app.summarizer import generate_summary
# summary = generate_summary(transcript)
# enviar notificação ao frontend
return True