import {logger, task} from "@trigger.dev/sdk";

interface TranscribePayload {
    job_id: string;
    file_path?: string;
    file_url?: string;
    language: string;
    webhook_url: string;
}

interface TranscribeResult {
    success: boolean;
    job_id: string;
    message: string;
    modal_result?: any;
    error?: string;
}

export const transcribeAudio = task({
    id: "transcribe-audio",
    maxDuration: 3600, // 1 hora máximo
    retry: {
        maxAttempts: 3,
        factor: 2,
        minTimeoutInMs: 5000,
        maxTimeoutInMs: 30000,
        randomize: false,
    },
    run: async (payload: TranscribePayload): Promise<TranscribeResult> => {
        logger.log("🎵 Iniciando transcrição", {
            job_id: payload.job_id,
            language: payload.language,
            has_file_path: !!payload.file_path,
            has_file_url: !!payload.file_url
        });

        try {
            // Validar payload
            if (!payload.job_id) {
                throw new Error("job_id é obrigatório");
            }

            if (!payload.file_path && !payload.file_url) {
                throw new Error("É necessário fornecer file_path ou file_url");
            }

            if (!payload.webhook_url) {
                throw new Error("webhook_url é obrigatório");
            }

            // Notificar início do processamento
            logger.log("📡 Notificando início do processamento", {job_id: payload.job_id});

            try {
                await fetch(payload.webhook_url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        job_id: payload.job_id,
                        status: 'processing',
                        message: 'Transcrição iniciada'
                    }),
                });
            } catch (webhookError) {
                logger.warn("⚠️ Erro ao notificar início", {error: webhookError});
                // Não é crítico, continua o processamento
            }

            // Preparar dados para Modal
            const modalPayload = {
                job_id: payload.job_id,
                file_path: payload.file_path,
                file_url: payload.file_url,
                language: payload.language || "auto",
                webhook_url: payload.webhook_url,
            };

            logger.log("🚀 Preparando chamada para Modal", {
                job_id: payload.job_id,
                modal_url: process.env.MODAL_WEBHOOK_URL
            });

            // Chamar Modal via HTTP
            const modalUrl = process.env.MODAL_WEBHOOK_URL;
            if (!modalUrl) {
                throw new Error("MODAL_WEBHOOK_URL não está configurada");
            }

            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };

            if (process.env.MODAL_TOKEN_SECRET) {
                headers['Authorization'] = `Bearer ${process.env.MODAL_TOKEN_SECRET}`;
            }

            const modalResponse = await fetch(modalUrl, {
                method: 'POST',
                headers,
                body: JSON.stringify(modalPayload),
            });

            if (!modalResponse.ok) {
                const errorText = await modalResponse.text();
                throw new Error(`Modal API erro ${modalResponse.status}: ${errorText}`);
            }

            const modalResult = await modalResponse.json();

            logger.log("✅ Modal chamado com sucesso", {
                job_id: payload.job_id,
                modal_status: modalResponse.status
            });

            return {
                success: true,
                job_id: payload.job_id,
                message: "Transcrição iniciada no Modal",
                modal_result: modalResult,
            };

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);

            logger.error("❌ Erro ao processar transcrição", {
                job_id: payload.job_id,
                error: errorMessage,
                stack: error instanceof Error ? error.stack : undefined
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
                        error_message: errorMessage,
                        message: 'Erro ao iniciar transcrição'
                    }),
                });

                logger.log("📡 Webhook de erro notificado", {job_id: payload.job_id});
            } catch (webhookError) {
                logger.error("❌ Erro ao notificar webhook", {
                    job_id: payload.job_id,
                    webhook_error: webhookError instanceof Error ? webhookError.message : String(webhookError)
                });
            }

            return {
                success: false,
                job_id: payload.job_id,
                message: "Erro ao processar transcrição",
                error: errorMessage
            };
        }
    },
});