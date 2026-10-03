# Smart Study Notes Generator

## Status and scope

Source application prepared for a Python 3.11 environment. It has not been executed, model-tested, or deployed by the assistant. Included automated tests must be run before claiming readiness. There are no verified model outputs yet. Earlier chat sample outputs and word counts are not evaluation evidence.

This version uses the Hugging Face Transformers summarization pipeline directly rather than the previously suggested remote inference endpoint. No API key is needed. Input is processed on the Python server. The first run downloads the pretrained model. Model inference can be slow on a CPU and needs substantial memory; hosting resource limits must be checked. This is a small educational application, not a hardened public multi-tenant service.

## Files

Save the downloaded source files as `app.py`, `test_app.py`, and `requirements.txt` in the same folder. If downloads end in `.txt`, rename the Python files before starting. Save this document as `README.md`.

## Install and launch

Use Python 3.11. In that folder:

```bash
python -m venv .venv
```

Windows activation:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux activation:

```bash
source .venv/bin/activate
```

Install and check:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q app.py test_app.py
python -m unittest -v test_app
python -m streamlit run app.py
```

Open the local address printed by Streamlit, usually `http://localhost:8501`. The interface starts before the AI model is downloaded. Generate notes or run the project tests to initialize the model.

## Usage

Enter an English paragraph of at least 20 words. Choose summary length and number of key points, then generate notes. The application displays actual word counts, signed reduction percentage, extracted key sentences, and a Markdown download. Outputs remain available during UI reruns. Up to ten results are kept in browser-session state, not in a database.

Reduction = (original words - summary words) / original words * 100.

A negative reduction is shown honestly if a generated summary is longer. Word count treats apostrophes and hyphenated words as parts of one word. Generation lengths use model tokens, not words. Input beyond 900 model tokens is rejected without silently discarding any text.

## Required three-paragraph evaluation

Open the Project tests tab and click Run three project tests. This performs real model inference on Artificial Intelligence, Water Cycle, and Physical Exercise. The table records each original paragraph, actual generated summary, extracted key points, word counts, reduction, model name, model revision when available, library version, and UTC timestamp. Failed cases are marked and are not treated as completed evaluations.

Read every summary before writing the observation. Assess whether it preserves the central ideas, adds unsupported facts, omits important details, and reads coherently. Enter the observation in the provided field, then download the CSV. Do not treat a nonempty summary as proof of relevance or coherence.

Observation template, to complete only after running:

“Across the three examples, the summaries [preserved/partly preserved] the main ideas. The AI example retained [details]; the water-cycle example retained [stages]; the exercise example retained [benefits]. Sentence flow was [assessment]. Important omissions or unsupported statements were [findings]. The measured reductions were [actual percentages].”

## Automated checks

The unit tests cover counting, signed reductions, validation, key-point ordering, export, token limits, and mocked model behavior. An interface test checks loading an example and clearing input. Mock-based tests do not establish model quality. Run the three actual model evaluations separately.

After checks pass, lock the tested environment for deployment if desired:

```bash
python -m pip freeze > requirements-lock.txt
```

## Online deployment

Upload app.py and requirements.txt to your own GitHub repository, along with the tests and README. Connect that repository in Streamlit Community Cloud, choose the branch, set app.py as the entry point, select Python 3.11, and deploy. No secrets are needed for this implementation. Deployment must be performed in your hosting account; no public URL has been created here.

The model is shared across sessions with an inference lock. Personal text and outputs are not cached globally. Resource-limited hosts may be unable to load the model; use a host with sufficient RAM or an authenticated, verified inference service instead. Do not silently replace failed AI generation with a non-AI summary for project evaluation.

## Limitations and privacy

The model is oriented toward English summarization and can omit details or hallucinate. Key points use frequency-ranked original sentences rather than a generative model. Sentence splitting is heuristic and may mishandle abbreviations. Summary length is approximate. No login, persistent storage, billing, rate limiting, or database is included. Add authentication and request limits before exposing a costly service broadly. Browser-session data is temporary, but no retention guarantee is made for third-party hosting infrastructure. Do not upload sensitive text.

## References

Hugging Face summarization: https://huggingface.co/tasks/summarization

Model: https://huggingface.co/sshleifer/distilbart-cnn-12-6

Streamlit deployment: https://docs.streamlit.io/deploy/streamlit-community-cloud

Model guidance checked October 3, 2026.
