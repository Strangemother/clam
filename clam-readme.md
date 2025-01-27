+ Conversation here: https://chatgpt.com/share/dfdcffee-2881-44a1-a417-0d61de8ca37f

> First draft, using GPT as a dictation machine 

# Clustered Little Action Model (CLAM)

## Overview
The Clustered Little Action Model (CLAM) is an innovative concept aimed at enhancing machine learning processes. It involves using multiple small language models (tiny neural nets) on separate CPUs to process the same input request. The responses from these models are then analyzed collectively to produce a reliable output.

## Concept
- **CLAM** stands for **Clustered Little Action Model**.
- It uses multiple small language models (tiny neural nets) on separate CPUs.
- Each model processes the same input request independently.
- Responses are collected and analyzed by a central function.
- The goal is for the central function to validate the responses using a verification model (similar to NASA's verification process).

## Process
1. **Input Request:** An input request is sent to each small language model.
2. **Response Collection:** Each model attempts to respond to the request.
3. **Validation:** The central function collects all responses and validates them.
4. **Output Generation:** The function generates the final output based on the validated responses.

## First Iteration
- **Basic Function:** The initial central function will be basic, focusing on simple tokenization and diffing.
- **Failure Handling:** If responses are too varied, the function will attempt to micro-train the models by making slightly modified input requests.

## Implementation
- **Model Usage:** Use multiple instances of a simple model like QUEN 0.5b for text analysis.
- **Cluster Setup:** Deploy these models across various websites to collect actions.
- **Scalability:** Add more micro-training clusters to the CLAM model for new actions.

## Advantages
1. **Efficiency:** More efficient than training a supersized action model on small machinery.
2. **Flexibility:** Ability to run small models and deploy them as needed.
3. **Scalability:** Utilizes multiple models, both large and small, allowing for future reductions in the number of models.
4. **Modularity:** Micro language models with a rag topology can be switched out and trained on the fly, based on user input and AI's prompting action.

## Tipping Function
- **Inference Models:** Micro language models process inputs and outputs, and can be micro-trained without long training processes.
- **Response Analysis:** The central function analyzes the list of outputs and performs a simple abstraction to determine the best fit.
- **Graph Theory Analysis:** Uses a methodology similar to simple graph theory analysis with keys to resolve the set of results against the allowed results.

## Performance
- **Speed:** While processing through many models linearly may take longer, having multiple micro models reduces the complexity of decisions, resulting in fast enough responses for localized action models without excessive complexity.

## Feedback System (Victory Model)
1. **Success or Failure Detection:** The CLAM model listens for another input after producing an output. If the user provides feedback, such as "well done" or "bad answer," this feedback is used to inform the tipping function.
2. **Reevaluation:** The feedback is used to reanalyze the path produced by the models, identifying which models succeeded or failed.
3. **Reattempt:** The system attempts to reprocess the input, adjusting the CLAM action inputs or the weights within the tipping function to produce a more accurate response.

## Weighting Mechanism
1. **Truthfulness Weighting:** Each model has an associated numerical value representing its truthfulness. By default, this value is 1, but it can be adjusted based on performance.
2. **Weight Adjustment:** Successful outputs increase a model's weight, while failures decrease it. This dynamic weighting allows for the integration of new models with initial lower or higher weights.
3. **Super Weights:** Superior models (e.g., GPT) with high accuracy will have massive weights, influencing the tipping function more strongly. When a super-weighted model succeeds, it sets a precedent for other models, potentially prompting re-evaluation of their responses.

## Prompt Generalization and Ripple Effect
1. **Prompt Impact:** Changing a prompt for a CLAM model can affect other responses. For example, a model that correctly identifies "kettle" in one context might produce incorrect results in another if retrained improperly.
2. **Cached Outputs:** To address this, the system uses cached outputs with associated weights. If a past correct response is identified (e.g., "kettle"), it is heavily weighted, ensuring consistency in similar contexts.
3. **Multiple Inputs:** The CLAM model needs to handle multiple inputs
