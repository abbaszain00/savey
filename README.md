# Savey 💾

A stateful personal expense tracking agent built with LangGraph and OpenRouter.

## Setup

1. Clone the repo
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project root:
   ```
   OPENROUTER_API_KEY=your-key-here
   ```

## Usage

```bash
python main.py
```

- Type your expenses naturally: `I bought a £4.50 coffee today.`
- Type `/state` to see your current expense summary
- Type `exit` to end the session

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Open a Pull Request into `main`
