import { logger, task } from "@trigger.dev/sdk";

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

      // Preparar dados para Modal
      const modalPayload = {
        job_id: payload.job_id,
        file_path: payload.file_path,
        file_url: payload.file_url,
        language: payload.language,
        webhook_url: payload.webhook_url,
      };

      logger.log("Preparando chamada para Modal", { job_id: payload.job_id });

      // Chamar Modal via HTTP (método mais confiável)
      const modalUrl = process.env.MODAL_WEBHOOK_URL || "https://your-modal-app.modal.run/transcribe";

      const response = await fetch(modalUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.MODAL_TOKEN_SECRET}`,
        },
        body: JSON.stringify(modalPayload),
      });

      if (!response.ok) {
        throw new Error(`Modal API retornou erro: ${response.status} - ${response.statusText}`);
      }

      const modalResult = await response.json();

      logger.log("Modal chamado com sucesso", {
        job_id: payload.job_id,
        modal_response: modalResult
      });

      return {
        success: true,
        job_id: payload.job_id,
        message: "Transcrição iniciada no Modal",
        modal_result: modalResult,
      };

    } catch (error) {
      logger.error("Erro ao processar transcrição", {
        job_id: payload.job_id,
        error: error instanceof Error ? error.message : String(error)
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
            error_message: error instanceof Error ? error.message : String(error),
            message: 'Erro ao iniciar transcrição no Modal'
          }),
        });
      } catch (webhookError) {
        logger.error("Erro ao notificar webhook", {
          error: webhookError instanceof Error ? webhookError.message : String(webhookError)
        });
      }

      throw error;
    }
  },
});