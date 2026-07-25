# Golden Demo Source 05: Prompt Engineering Lab Notes

Prompt engineering is the practice of shaping instructions, context, constraints, and examples so an AI system produces a useful response. A strong prompt states the task, defines the audience, names the source boundary, and asks for a verifiable output format.

For document-grounded work, prompt engineering should not override evidence. The prompt can request a concise explanation, a comparison, a marks-ready answer, or a research paragraph, but the answer must still use the retrieved source material. If the source does not contain enough evidence, the correct behavior is to ask for more context or say that the answer is not found in the uploaded material.

Useful prompt patterns include role framing, task decomposition, output constraints, citation requirements, and refusal rules. Role framing tells the assistant what kind of help is needed. Task decomposition breaks a large request into smaller steps. Output constraints keep the answer readable. Citation requirements connect claims to source passages. Refusal rules prevent unsupported invention.

A poor prompt asks for an impressive answer without source limits. A better prompt asks for a clear answer from the selected document, with citations per paragraph when useful, and a short note if evidence is weak.

