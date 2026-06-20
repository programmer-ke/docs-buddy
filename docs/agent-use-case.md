## Use Case: AI-Assisted Documentation Search (Single Turn)

**Title:** Retrieve Information from Documentation with AI Agent Using Search Tool

**Primary Actor:** User (client-agnostic: CLI, web form, etc.)

**Preconditions:**
1. The documentation index has been built (repositories synced and chunks indexed).
2. An AI agent is available and configured with a search tool.

**Postconditions (success):**
1. The user receives a structured response containing:
   - The AI agent's synthesized answer.
   - A list of citations (document URLs) referencing the source chunks used.
2. The system logs the query and results for observability.

**Main Success Flow:**
1. User submits a natural language question.
2. System routes the question to the AI agent.
3. Agent calls the search tool with the user's question (and optionally a max_results parameter).
4. Search tool queries the document index and returns a ranked list of relevant chunks.
5. Agent selects a subset of chunks it deems relevant to the question.
6. Agent synthesizes an answer from the selected chunks.
7. System returns the structured response (answer + citations) to the user.

**Error Paths (in scope):**
- **Index not built:** System returns an error message indicating the documentation index is not available.
- **Invalid query:** If the query is empty or malformed, system returns an appropriate validation error to the user.

**Open/Deferred Items:**
- Exact parameters of the search tool interface (to be determined at implementation).
- Multi-turn dialogue (out of scope for initial version).
- Client-specific rendering of the structured response (to be determined by each client).
