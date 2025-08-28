// @ts-ignore
import { Trigger } from "@trigger.dev/sdk";

const client = new Trigger({
  id: "echo-trigger",
  apiKey: process.env.TRIGGER_API_KEY!,
});

client.defineJob({
  id: "transcription-complete",
  name: "Handle transcription complete",
  version: "1.0.0",
  trigger: client.eventTrigger("transcription.complete"),
  run: async (payload) => {
    console.log("Received transcription result:", payload);
  },
});

client.run();
