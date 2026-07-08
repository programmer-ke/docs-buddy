# TODO List

Status legend:
 - [ ] todo
 - [>] in progress
 - [x] done

## todo

- [ ] address todo comments



- [ ] **US-007: User can submit a query via CLI and receive a structured response**  
  *As a user, I want to submit a query via the CLI and receive the structured response (answer + citations) printed to the console, so that I can use the system from the command line.*  
  - [ ] **Scenario 7.1:** CLI query returns answer and citations  
    Given the documentation index has been built  
    And the AI agent is configured  
    When the user runs `docs-buddy query "What is X?"`  
    Then the CLI prints the answer and the list of citations  
	- CLI design decisions:
	  - configuration
	    - use hostname + path as repo id e.g. github.com/programmer-ke/docs-buddy
		- specify the raw file url in config
		- use yaml config files for conf
		- walk up from current to home directory to find config file
		  - add a flag to show user the config file used for current invocation
		  - Add a flag to create config file from template in current location
	
  - [ ] **Scenario 7.2:** CLI query returns error message  
    Given the documentation index has not been built  
    When the user runs `docs-buddy query "What is X?"`  
    Then the CLI prints the error message: "Documentation index is not available. Please sync a repository first."

- [ ] **US-008: User can submit a query via web form and receive a structured response**  
  *As a user, I want to submit a query via a web form and receive the structured response (answer + citations) rendered in the browser, so that I can use the system from a web interface.*  
  - [ ] **Scenario 8.1:** Web form query returns answer and citations  
    Given the documentation index has been built  
    And the AI agent is configured  
    When the user submits a query via the web form  
    Then the web page displays the answer and the list of citations  
  - [ ] **Scenario 8.2:** Web form query returns error message  
    Given the documentation index has not been built  
    When the user submits a query via the web form  
    Then the web page displays the error message: "Documentation index is not available. Please sync a repository first."


## in progress


## done

- [x] **US-006: Operator can observe logs**  
  *As an operator, I want to see logs of each query submitted and the corresponding result (answer + citations), so that I can monitor usage, debug issues, and audit the system.*  
  - [x] **Scenario 6.1:** Query logged on success  
    Given the system is running  
    When a user submits a valid query and receives a successful response  
    Then the system logs: search args, agent events  
- [x] **US-005: User can submit a query and receive an answer
  synthesized by an AI agent using the search tool*
  *As a user, I want to submit a query and receive an answer
  synthesized by an AI agent that uses the search tool to retrieve
  relevant chunks, so that I get a natural language answer grounded in
  the documentation.*
  - [x] **Scenario 5.1:** AI agent returns answer with citations  
    Given the documentation index has been built and contains indexed chunks  
    And an AI agent is configured with the search tool  
    When the user submits a valid query  
    Then the system returns a structured response where:  
      - The `answer` field contains a natural language answer synthesized by the agent  
      - The `citations` field contains document URLs of chunks the agent selected  
  - [x] **Scenario 5.2:** AI agent decides no chunk is relevant  
    Given the documentation index has been built and contains indexed chunks  
    And an AI agent is configured with the search tool  
    When the user submits a valid query  
    And the agent decides none of the returned chunks are relevant  
    Then the system returns a structured response where:  
      - The `answer` field contains a message like "I could not find relevant information in the documentation."  
      - The `citations` field is an empty list  
  - [x] **Scenario 5.3:** Search returns zero chunks  
    Given the documentation index has been built but contains no chunks matching the query  
    And an AI agent is configured with the search tool  
    When the user submits a valid query  
    Then the system returns a structured response where:  
      - The `answer` field contains a message like "I could not find relevant information in the documentation."  
      - The `citations` field is an empty list
- [x] **US-004: User can submit a query and receive a real answer from the document index (no AI agent yet)**  
  *As a user, I want to submit a query and receive an answer synthesized from the document index using a simple deterministic strategy (e.g., return the top chunk text as the answer), so that I can validate the search and retrieval pipeline end-to-end.*  
  - [x] **Scenario 4.1:** Query returns top chunk as answer  
    Given the documentation index has been built and contains indexed chunks  
    When the user submits a valid query  
    Then the system returns a structured response where:  
      - The `answer` field contains the text of the top-ranked chunk  
      - The `citations` field contains the document URL of that chunk  
  - [x] **Scenario 4.2:** Query with no matching chunks  
    Given the documentation index has been built but contains no chunks matching the query  
    When the user submits a valid query  
    Then the system returns a structured response where:  
      - The `answer` field is an empty string  
      - The `citations` field is an empty list
- [x] **US-003: User can submit a query and receive a hardcoded answer with a hardcoded citation**  
  *As a user, I want to submit a query and receive a hardcoded answer with a hardcoded citation, so that I can see the end-to-end flow working (even if the answer is not real) and validate the response structure.*  
  - [x] **Scenario 3.1:** Query submitted returns hardcoded answer  
    Given the documentation index has been built  
    And the query is valid  
    When the user submits any query  
    Then the system returns a structured response containing:  
      - A hardcoded answer text (e.g., "This is a placeholder answer.")  
      - One hardcoded citation in the output text (e.g., `"https://example.com/doc"`)  
- [x] **US-002: User can submit a natural language query and receive a validation error for empty or malformed input**  
  *As a user, I want to receive a validation error when I submit an empty or malformed query, so that I know my input was not accepted and I can correct it.*  
  - [x] **Scenario 2.1:** Empty query submitted  
    Given the documentation index has been built  
    When the user submits an empty string as the query  
    Then the system returns a validation error: "Query cannot be empty."  
  - [x] **Scenario 2.2:** Malformed query submitted (e.g., only whitespace)  
    Given the documentation index has been built  
    When the user submits a query consisting only of whitespace  
    Then the system returns a validation error: "Query cannot be empty."  
  - [x] **Scenario 2.3:** Valid query submitted  
    Given the documentation index has been built  
    When the user submits a non-empty, non-whitespace query  
    Then the system does not return a validation error
- [x] brainstorm agent implementation
- [x] refactor to use commands/events/message-bus
- [x] Implement lexical search over document index

## Parked

- [x] **US-001: User can submit a natural language query and receive a "no index" error** (this should be caught by bootstrap)
  *As a user, I want to submit a natural language question and get a clear error message when the documentation index has not been built, so that I know the system is not ready and I can take action (e.g., trigger a sync).* 
  - [ ] **Scenario 1.1:** Query submitted with no index built 
    Given the documentation index has not been built 
    When the user submits a natural language question 
    Then the system returns an error message: "Documentation index is not available. Please sync a repository first."  
  - [ ] **Scenario 1.2:** Query submitted after index is built 
    Given the documentation index has been built 
    When the user submits a natural language question 
    Then the system does not return the "no index" error
