import { logger, task } from "@trigger.dev/sdk/v3";
import Modal from "@modal-labs/modal";

const modal = new Modal({
  tokenId: process.env.MODAL_TOKEN_ID!,
  tokenSecret: process.env.MODAL_TOKEN_SECRET!,
});

export const transcribeAudio = task({
  id: "transcribe-audio",
  maxDuration: 3600, // 1 hora máximo
  retry: {
    maxAttempts: 3,
    factor: 2,
    minTimeoutInMs: 5000,
    maxTimeoutInMs: 30000,
  },
  run: async (payload: {
    job_id: string;
    file_path?: string;
    file_url?: string;
    language: string;
    webhook_url: string;
  }) => {
    logger.log("Iniciando transcrição", {
      job_id: payload.job_id,
      language: payload.language,
      has_file_path: !!payload.file_path,
      has_file_url: !!payload.file_url
    });

    try {
      // Validar payload
      if (!payload.file_path && !payload.file_url) {
        throw new Error("É necessário fornecer file_path ou file_url");
      }

      if (!payload.webhook_url) {
        throw new Error("webhook_url é obrigatório");
      }

      // Chamar função Modal (fire-and-forget)
      // A função Modal já cuida do webhook, então só precisamos disparar
      const modalFunction = modal.Function.lookup("whisperx-transcriber", "transcribe_audio");

      // Invocar de forma assíncrona (não aguardar resultado)
      await modalFunction.spawn({
        job_id: payload.job_id,
        file_path: payload.file_path,
        file_url: payload.file_url,
        language: payload.language,
        webhook_url: payload.webhook_url,
      });

      logger.log("Função Modal disparada com sucesso", { job_id: payload.job_id });

      return {
        success: true,
        job_id: payload.job_id,
        message: "Transcrição iniciada no Modal",
      };

    } catch (error) {
      logger.error("Erro ao processar transcrição", {
        job_id: payload.job_id,
        error: error.message
      });

      // Notificar webhook sobre o erro
      try {
        await fetch(payload.webhook_url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            job_id: payload.job_id,
            status: 'failed',
            error_message: error.message,
            message: 'Erro ao iniciar transcrição no Modal'
          }),
        });
      } catch (webhookError) {
        logger.error("Erro ao notificar webhook", { error: webhookError.message });
      }

      throw error;
    }
  },
});