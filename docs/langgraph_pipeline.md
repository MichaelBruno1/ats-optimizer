# LangGraph Multi-Agent Pipeline Documentation

The **ATS Resume Optimizer** uses **LangGraph** to orchestrate multi-agent operations across resume analysis, job analysis, resume optimization, and PDF generation.

---

## 1. Pipeline Topology

```mermaid
graph TD
    START((START)) ──┬──> analyze_resume
                    └──> analyze_jobs
    analyze_resume ──> check_analyses{should_optimize?}
    analyze_jobs   ──> check_analyses
    check_analyses ──>|"analyses OK"| optimize
    check_analyses ──>|"error / missing"| END_ERR((END))
    optimize       ──> check_opt{should_generate?}
    check_opt      ──>|"optimization OK"| generate_pdfs
    check_opt      ──>|"error"| END_ERR2((END))
    generate_pdfs  ──> finalize
    finalize       ──> END((END))
```

### Key Topology Features:
- **Fan-Out Execution**: `analyze_resume` and `analyze_jobs` run concurrently directly from `START`.
- **Fan-In Convergence**: Both analysis nodes stream partial state updates into `should_optimize`.
- **Conditional Routing**: Edges short-circuit the pipeline to `END` if upstream nodes encounter errors.
- **Real-Time Progress**: Each node publishes SSE progress payloads directly to `state["queue"]`.

---

## 2. Graph State (`GraphState`)

Located in `app/graph/state.py`:

```python
class GraphState(TypedDict, total=False):
    session_id: str
    resume_text: str
    jobs: list[JobInput]
    output_mode: str  # "single" | "per_job"
    queue: Any  # asyncio.Queue for SSE events
    resume_analysis: Optional[ResumeAnalysis]
    job_analyses: Optional[list[JobAnalysis]]
    optimized_resumes: Optional[list[OptimizedResume]]
    optimization_results: Optional[list[OptimizationResult]]
    pdf_generated: bool
    error: Optional[str]
```

---

## 3. Nodes Breakdown

Located in `app/graph/nodes.py`:

| Node Name | Wrapped Operation | SSE Progress Range | Output State Keys |
|---|---|---|---|
| `analyze_resume` | `ResumeAnalystAgent().analyze()` | 5% → 20% | `resume_analysis` |
| `analyze_jobs` | `JobAnalystAgent().analyze()` × N | 25% → 50% | `job_analyses` |
| `optimize` | `ResumeOptimizerAgent().optimize_*()` | 55% → 75% | `optimized_resumes` |
| `generate_pdfs` | `generate_pdf()` in thread pool | 80% → 95% | `optimization_results`, `pdf_generated` |
| `finalize` | Serializes `result.json` & completes stream | 100% (complete) | None |

---

## 4. Conditional Edges

Located in `app/graph/edges.py`:

- **`should_optimize(state)`**: Returns `"optimize"` if both `resume_analysis` and `job_analyses` are present and `error` is `None`. Returns `"end"` otherwise.
- **`should_generate(state)`**: Returns `"generate_pdfs"` if `optimized_resumes` is present and `error` is `None`. Returns `"end"` otherwise.

---

## 5. Reusable Subgraphs

Located in `app/graph/pipeline.py`:

1. **`resume_analysis_subgraph`**: Runs `START → analyze_resume → END`.
2. **`job_analysis_subgraph`**: Runs `START → analyze_jobs → END`.
3. **`optimization_subgraph`**: Runs `START → optimize → should_generate? → generate_pdfs → finalize → END`.

---

## 6. API Integration

The API router in `app/api/router.py` initiates execution in `POST /api/v1/analyze`:

```python
asyncio.create_task(
    run_graph_pipeline(
        session_id=session_id,
        resume_text=resume_text,
        jobs=job_list,
        output_mode=output_mode,
        queue=queue,
    ),
    name=f"pipeline-{session_id}",
)
```

`run_graph_pipeline` calls `await optimization_graph.ainvoke(initial_state)` and puts `__DONE__` on the queue in a `finally` block to cleanly terminate the SSE stream.
