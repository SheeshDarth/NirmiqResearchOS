# Golden Demo Source 07: Module 5 Generative AI Notes

Generative AI systems create new text, images, code, or other content by learning patterns from data. Large language models generate text by predicting likely next tokens from context. Their output can be fluent, but fluency is not the same as truth.

Retrieval augmented generation adds an evidence step before generation. Instead of asking a model to answer only from memory, the system retrieves relevant passages and uses them as grounded context. This improves factuality when the retrieved material is relevant and complete.

Generative AI risks include hallucination, privacy leakage, bias, prompt injection, and overreliance. Hallucination happens when the model produces unsupported claims. Privacy leakage can happen when sensitive content is sent to an external service without clear consent. Prompt injection happens when malicious instructions inside a document try to override the user's actual goal.

Evaluation should test both usefulness and safety. Useful answers are relevant, readable, and complete enough for the task. Safe answers stay inside the source boundary, cite evidence, and refuse questions that the uploaded material cannot answer.

For fact-checking and verification, the module recommends cross-checking important claims against trusted sources. Retrieval-based methods should surface the passages used as evidence, and fallback responses should admit uncertainty when the material is incomplete or unclear.
