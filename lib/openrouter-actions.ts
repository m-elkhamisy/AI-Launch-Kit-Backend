// lib/openrouter-actions.ts
"use server";

import { openrouter } from "./openrouter";

// Wrap your API logic inside an async function (Server Action)
export async function generateTextWithOpenRouter(prompt: string) {
  try {
    const response = await openrouter.chat.completions.create({
      model: "meta-llama/llama-3-8b-instruct:free",
      messages: [{ role: "user", content: prompt }],
    });
    return response.choices[0].message.content;
  } catch (error) {
    // You can handle or throw errors here
    throw new Error("Failed to fetch from OpenRouter");
  }
}
