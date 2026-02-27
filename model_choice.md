# Person B Deliverable: Model Choice

## Selected Model: Google Gemini 1.5 Flash

### Reasoning
1.  **Cost (Free Tier)**: Gemini 1.5 Flash offers a generous free tier, making it accessible without upfront costs, which aligns with the "best and free" requirement.
2.  **Performance**: It is highly capable for summarization, reformatting, and explanation tasks required by this project.
3.  **Speed**: It is optimized for low latency, ensuring the bot responds quickly to user queries.
4.  **Safety**: Built-in safety settings help reinforce the "Person A" safety boundaries.

### Integration Strategy
- **API**: Google Generative AI SDK (`google-generativeai`).
- **Authentication**: API Key managed via environment variables.
- **Usage**: The model will be used strictly as a "formatter/explainer" engine. It will be fed the trusted content from Person A in its context window and instructed to answer ONLY based on that content.

### Alternatives Considered
- **OpenAI (GPT-3.5/4o-mini)**: Good options, but the free tier limits on the API are often stricter or non-existent compared to Gemini's free tier for developers.
- **Open-source (HuggingFace Local)**: Requires significant compute resources (GPU) to run locally, which adds complexity and may not be "free" if hardware upgrades are needed.
