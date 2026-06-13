"""Quiz content for default HireMeNow skills (10–15 questions each, 4 options)."""

from __future__ import annotations

from typing import TypedDict


class Option(TypedDict):
    body: str
    is_correct: bool


class Question(TypedDict):
    body: str
    options: list[Option]


class SkillSeed(TypedDict):
    name: str
    description: str
    pass_threshold: int
    questions: list[Question]


def q(body: str, correct: str, wrong: tuple[str, str, str]) -> Question:
    opts: list[Option] = [{"body": correct, "is_correct": True}]
    opts.extend({"body": w, "is_correct": False} for w in wrong)
    return {"body": body, "options": opts}


SKILLS: list[SkillSeed] = [
    {
        "name": "HTML-CSS",
        "description": "Markup structure, styling, layout, and responsive web fundamentals.",
        "pass_threshold": 70,
        "questions": [
            q("What does HTML stand for?", "HyperText Markup Language", ("HighText Machine Language", "Hyper Transfer Markup Language", "Home Tool Markup Language")),
            q("Which CSS property controls text size?", "font-size", ("text-size", "font-weight", "text-style")),
            q("Which HTML tag defines the largest heading?", "<h1>", ("<head>", "<heading>", "<h6>")),
            q("What does CSS stand for?", "Cascading Style Sheets", ("Creative Style Sheets", "Computer Style Sheets", "Colorful Style Sheets")),
            q("Which attribute specifies an image URL in HTML?", "src", ("href", "link", "url")),
            q("In Flexbox, flex-direction: column sets the main axis to:", "Vertical", ("Horizontal", "Diagonal", "Radial")),
            q("box-sizing: border-box means width includes:", "Padding and border", ("Only content", "Margin and padding", "Border only")),
            q("Which selector typically has the highest specificity?", "#id", (".class", "element", "*")),
            q("Which element is best for a site navigation block?", "<nav>", ("<section>", "<div>", "<span>")),
            q("display: none compared to visibility: hidden:", "Removes element from layout flow", ("Keeps space in layout", "Makes text transparent only", "Disables pointer events only")),
            q("Which unit is relative to the root element font size?", "rem", ("em", "px", "vh")),
            q("The viewport meta tag is mainly used for:", "Responsive layout on mobile devices", ("SEO ranking", "Caching pages", "Loading fonts")),
        ],
    },
    {
        "name": "Vanilla Javascript",
        "description": "Core JavaScript syntax, DOM APIs, async patterns, and browser fundamentals.",
        "pass_threshold": 70,
        "questions": [
            q("Which keyword declares a block-scoped variable?", "let", ("var", "define", "static")),
            q("typeof null in JavaScript returns:", "object", ("null", "undefined", "boolean")),
            q("Which method adds an element at the end of an array?", "push", ("pop", "shift", "unshift")),
            q("== vs === in JavaScript:", "=== compares value and type", ("== compares type only", "=== allows coercion", "They are identical")),
            q("An arrow function ( => ) does NOT have its own:", "this binding", ("return statement", "parameters", "body")),
            q("Promise states include:", "pending, fulfilled, rejected", ("open, closed, waiting", "start, run, stop", "idle, active, done")),
            q("document.querySelector() returns:", "The first matching element", ("All matching elements", "A NodeList always", "Only IDs")),
            q("JSON.parse() is used to:", "Convert a JSON string to a JavaScript value", ("Stringify an object", "Validate HTML", "Fetch remote data")),
            q("setTimeout(fn, 0) schedules the callback:", "After current synchronous code runs", ("Immediately in parallel", "Before any other task", "Only once page loads")),
            q("Which loop iterates over enumerable object keys?", "for...in", ("for...of on plain objects", "while...in", "each...of")),
            q("Array.map() returns:", "A new array with transformed values", ("The same array mutated", "A single value", "A Promise")),
            q("Strict mode ('use strict') helps by:", "Catching common coding mistakes", ("Disabling all errors", "Removing types", "Auto-minifying code")),
        ],
    },
    {
        "name": "C++",
        "description": "C++ syntax, memory, OOP, STL, and systems programming basics.",
        "pass_threshold": 70,
        "questions": [
            q("Which header is commonly used for cout and cin?", "<iostream>", ("<stdio.h>", "<stream>", "<console>")),
            q("int* p declares p as a:", "Pointer to int", ("Integer variable", "Reference to int", "Array of int")),
            q("Which access specifier allows class-only access?", "private", ("public", "global", "external")),
            q("std::vector differs from C arrays because it:", "Can grow dynamically", ("Is always fixed size", "Stores only chars", "Cannot use iterators")),
            q("A C++ reference (&) must be:", "Initialized when declared", ("Nullable by default", "Reassigned to another object", "Always static")),
            q("Which keyword prevents inheritance of a class?", "final", ("static", "const", "sealed only in Java")),
            q("RAII in C++ stands for:", "Resource Acquisition Is Initialization", ("Random Access Iterator Interface", "Runtime Allocation In Initialization", "Reference And Instance Integration")),
            q("Which operator frees memory allocated with new?", "delete", ("free", "release", "destroy")),
            q("std::unique_ptr expresses:", "Exclusive ownership of a resource", ("Shared ownership", "Weak reference", "Stack-only storage")),
            q("A virtual function enables:", "Runtime polymorphism", ("Compile-time only binding", "Multiple inheritance removal", "Header-only templates")),
            q("const int& x means:", "Read-only reference to int", ("Mutable reference", "Pointer to const", "Constant pointer")),
            q("#include <algorithm> is often used for:", "sort, find, and other generic algorithms", ("File I/O only", "Threading only", "Network sockets")),
        ],
    },
    {
        "name": "FastAPI (Python)",
        "description": "Building async REST APIs with FastAPI, Pydantic, and Python typing.",
        "pass_threshold": 70,
        "questions": [
            q("FastAPI is built on top of:", "Starlette and Pydantic", ("Django ORM only", "Flask templates", "Tkinter")),
            q("Which decorator defines a GET route?", "@app.get()", ("@app.route(get=True)", "@api.read()", "@router.fetch()")),
            q("Pydantic models are mainly used for:", "Data validation and serialization", ("Database migrations", "HTML rendering", "CSS bundling")),
            q("Dependency injection in FastAPI uses:", "Depends()", ("Inject()", "@require", "middleware only")),
            q("To return JSON automatically you typically:", "Return a dict or Pydantic model", ("Call json.dumps manually always", "Use render_template", "Return bytes only")),
            q("async def route handlers allow:", "Non-blocking I/O with await", ("Only CPU-bound threading", "Synchronous DB only", "No concurrency")),
            q("OpenAPI docs in FastAPI are available at:", "/docs by default", ("/swagger only in production", "/api/schema hidden", "/redoc only")),
            q("HTTPException is used to:", "Return error responses with status codes", ("Catch Python exceptions globally", "Validate SQL", "Parse JWT only")),
            q("Path parameters are declared:", "In the route path with {name}", ("Only in query strings", "In request body only", "Via headers only")),
            q("BackgroundTasks lets you:", "Run work after sending a response", ("Replace Celery always", "Block the event loop", "Migrate databases")),
            q("APIRouter helps with:", "Organizing routes into modules", ("Replacing Uvicorn", "Deploying to AWS only", "Writing CSS")),
            q("Uvicorn is commonly used to:", "Serve the ASGI FastAPI application", ("Compile Python to C", "Manage PostgreSQL", "Bundle frontend assets")),
        ],
    },
    {
        "name": "ReactJS",
        "description": "Component model, hooks, state, and modern React UI development.",
        "pass_threshold": 70,
        "questions": [
            q("React components typically return:", "JSX (or React elements)", ("HTML files", "CSS modules only", "SQL queries")),
            q("useState returns:", "A state value and a setter function", ("Only a setter", "A Redux store", "A ref object")),
            q("Keys in a list help React:", "Identify which items changed", ("Style components", "Encrypt props", "Lazy-load routes")),
            q("useEffect runs after:", "Render commits to the screen", ("Before JSX parses", "Only on unmount", "Server startup")),
            q("Lifting state up means:", "Moving shared state to a common ancestor", ("Using global variables", "Duplicating state in children", "Removing props")),
            q("Controlled input value is driven by:", "React state via value/onChange", ("DOM default only", "localStorage always", "CSS variables")),
            q("React.Fragment (<>) is used to:", "Group elements without extra DOM nodes", ("Create portals", "Replace Router", "Fetch data")),
            q("Context API is useful for:", "Sharing data without deep prop drilling", ("Replacing all state", "Database access", "Bundling assets")),
            q("memo() helps optimize by:", "Skipping re-render when props are unchanged", ("Caching fetch requests", "Virtualizing lists only", "Parsing JSX faster")),
            q("useRef persists values:", "Across renders without causing re-render", ("Only inside useEffect", "Until page refresh only", "In sessionStorage")),
            q("Strict Mode in development:", "Double-invokes certain lifecycles to find bugs", ("Disables hooks", "Removes warnings", "Minifies JSX")),
            q("React Router handles:", "Client-side navigation between views", ("SQL migrations", "API authentication", "CSS preprocessing")),
        ],
    },
    {
        "name": "Agentic AI",
        "description": "Autonomous agents, tool use, planning loops, and multi-step AI workflows.",
        "pass_threshold": 70,
        "questions": [
            q("An AI agent differs from a single prompt call by:", "Planning and acting over multiple steps", ("Using only one token", "Ignoring tools", "Running without memory")),
            q("Tool use in agents allows the model to:", "Call external functions or APIs", ("Train new weights live", "Edit its own code unsafely", "Bypass safety filters")),
            q("ReAct pattern combines:", "Reasoning and acting in a loop", ("Retrieval and encryption", "React.js and transformers", "Ranking and clustering only")),
            q("Agent memory often stores:", "Past observations and decisions", ("Only system prompts", "GPU driver versions", "CSS variables")),
            q("A planner module typically:", "Breaks goals into subtasks", ("Renders HTML", "Compiles C++", "Hashes passwords")),
            q("Human-in-the-loop is used when:", "High-stakes actions need approval", ("Latency must be zero", "Tools are unavailable", "Models are deterministic")),
            q("Max iteration limits prevent:", "Infinite tool-call loops", ("All errors", "Token usage", "Logging")),
            q("Structured tool schemas help models:", "Produce valid arguments for functions", ("Increase hallucinations", "Skip validation", "Disable JSON")),
            q("Multi-agent systems may assign:", "Specialized roles to different agents", ("One model only", "No communication", "Fixed SQL queries")),
            q("Evaluation of agents often measures:", "Task success and step efficiency", ("Pixel color accuracy", "Bundle size", "DOM depth")),
            q("Guardrails in agent pipelines:", "Reduce unsafe or off-topic actions", ("Remove all logging", "Disable tools entirely", "Force single-shot answers")),
            q("Observability for agents includes:", "Tracing steps, tools, and outcomes", ("Hiding all prompts", "Deleting transcripts", "Disabling metrics")),
        ],
    },
    {
        "name": "LLM Basics",
        "description": "Large language models, tokens, prompting, context windows, and inference.",
        "pass_threshold": 70,
        "questions": [
            q("LLM stands for:", "Large Language Model", ("Linear Learning Machine", "Local Link Module", "Logical Layer Map")),
            q("Tokens are:", "Subword units the model processes", ("Always full words only", "Database rows", "GPU threads")),
            q("Temperature controls:", "Randomness of generated output", ("Model size", "Context length", "Training epochs")),
            q("Context window limits:", "How much text the model can consider at once", ("Output file size", "Number of users", "API rate only")),
            q("Zero-shot prompting means:", "No task-specific examples in the prompt", ("No system message", "No tokens", "No model weights")),
            q("Few-shot prompting includes:", "Example input-output pairs", ("Fine-tuned weights only", "RAG indexes only", "GPU kernels")),
            q("Hallucination refers to:", "Confident but incorrect generated content", ("Slow inference", "Token overflow", "Encrypted output")),
            q("Embeddings represent text as:", "Dense numerical vectors", ("Plain JSON files", "HTML tags", "SQL tables")),
            q("Top-p (nucleus) sampling:", "Samples from the smallest set of tokens above probability p", ("Always picks argmax", "Ignores probabilities", "Trains the model")),
            q("System prompts typically set:", "Behavior and role constraints", ("Database URLs", "CSS themes", "Binary weights")),
            q("RAG augments LLMs with:", "Retrieved external documents", ("Random noise", "Only fine-tuning", "Image pixels only")),
            q("Inference is:", "Running a trained model to generate outputs", ("Collecting training data", "Designing HTML", "Compiling C++")),
        ],
    },
]
