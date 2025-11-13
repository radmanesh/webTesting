## Meeting Agenda

### **Progress (What has been done)**

- **ResponsiveGen agent initiated**
- **Evaluation metrics extended**
  - Horizontal scroll availability (content exceeding viewport width)
  - Horizontal scroll position (initial, after scroll, reset)
  - Overflow element count (elements with horizontal overflow)
  - Viewport meta tag (presence and correctness)
  - Responsive media (responsive vs fixed-size images/videos)
  - Relative units (percentage-based vs pixel-based sizing)
  - Computed font sizes (minimum 12px across mobile/tablet/desktop)
  - Tap target sizes (minimum 48x48px for interactive elements)
  - Line spacing (minimum 1.5:1 line-height ratio)
  - Screenshot comparison (MSE, RMSE, percentage difference)

- **Layout similarity foundations (need double-checking)**
  - Layout Similarity Score (LSS): weighted IoU between test and ground truth HTML
  - Multi-scale layout scores: per-viewport similarity
  - Weighted IoU scoring
  - Multi-scale per-viewport scores

- **Ricky onboarding**
  - Reviewing codebase and HTML concepts
  - Rotation-friendly check (to be done independently)

---

### **Blocking Items / Open Questions**

#### ResponsiveGen Agent Structure
- **Memory**
- **Environment & tools**
  - Sandbox repo for generated HTML
  - Read, create, edit file content
  - Screenshot generation
  - Evaluation routing
  - Feedback and HTML improvement
  - Reading external resources via web

#### Evaluation
- Compare sketch viewport to screenshot viewport
- Sketch2Code’s hack used ground truth to guide inference
  - **Question:** Is it valid to use ground truth at inference for evaluation? (I disagree.)

#### EvaluationAgentRouter
- Dispatch tasks to correct evaluator agents

---

### **Planning Challenges**

- Complex planning without a trained planner may cause formatting issues
- **Task (Dispatch) Router** for:
  - Screenshot generation
  - File edits
  - File reading
  - Evaluation + feedback retrieval

- **Task Summarizer**
  - Summarize history or subtasks

- **Query Augmentation**
  - Improve prompts before generation

- **Task Manager / Orchestrator**
  - Manage tasks sequentially
  - Refine planning after each feedback step

---

### **Multi-Agent Approach**

- Use LangChain router to delegate tasks across agents
- Automatic evaluation + feedback loops to improve generation
- Question-Answering mode (to be explored)