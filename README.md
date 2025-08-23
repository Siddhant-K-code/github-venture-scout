# GitHub Venture Scout

A tool that analyzes GitHub profiles to identify investment-worthy projects. It uses AI to evaluate repositories through the lens of venture capital.

## What it does

This tool solves a specific problem: VCs and angels spend too much time manually reviewing GitHub profiles. It automates the initial screening by analyzing code repositories for commercial potential.

The analysis focuses on what matters for investment: market size, technical moat, team capability, and traction signals. Not just star counts.

## Installation

Clone the repository:
```bash
git clone https://github.com/Siddhant-K-code/github-venture-scout.git
cd github-venture-scout
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Set up credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
GITHUB_TOKEN=your_github_personal_access_token_here  # Optional
GEMINI_API_KEY=your_gemini_api_key_here              # Required
```

## Getting API Keys

### GitHub Token (Optional)
1. GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `public_repo`, `read:user`

Without token: 60 requests/hour. With token: 5,000 requests/hour.

### Gemini API Key (Required)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Get API Key

## Usage

Run:
```bash
python enhanced_analyzer.py
```

You'll be prompted for:
1. GitHub username
2. Analysis focus (1-5)
3. Analysis depth
4. Minimum stars filter
5. Maximum repositories

### Analysis Modes

1. **All repositories** - Complete portfolio analysis
2. **Most popular** - Top 10 by stars
3. **Recently active** - Last 10 updated (fastest, ~20 repos fetched)
4. **Top 20** - Top 20 by stars
5. **Actively maintained** - Updated in last 6 months (~50 repos fetched)

Default to mode 3 or 5 for speed. Modes 2 and 4 require fetching all repositories.

## Output

Two files are generated:

**Markdown Report** (`report_username_timestamp.md`)
- Investment opportunities ranked by potential
- Developer profile assessment
- Specific next steps for funding readiness

**JSON Report** (`report_username_timestamp.json`)
- Structured data for programmatic use
- Complete analysis metadata

## Evaluation Criteria

The tool evaluates eight factors:

1. Problem-Solution Fit
2. Market Size (TAM/SAM/SOM)
3. Technical Innovation
4. Competitive Advantage
5. Team Capability
6. Traction Indicators
7. Monetization Potential
8. Scalability

These mirror what VCs actually look for, not what developers think they look for.

## Performance

Smart fetching minimizes API calls:
- "Recently Active" fetches ~20 repos
- "Actively Maintained" fetches ~50 repos
- "Popular" modes require all repos

With GitHub token: 80x more API calls allowed.

## Project Structure

```
github-venture-scout/
├── enhanced_analyzer.py    # Main code
├── requirements.txt         # Dependencies
├── .env.example            # Environment template
├── .env                    # Your credentials
├── .gitignore
├── README.md
└── report_*.md/json       # Generated reports
```

## Common Issues

**User not found**: Check username spelling and profile visibility.

**Rate limit exceeded**: Add GitHub token or wait for reset.

**No repositories found**: Adjust filters or check if user has public repos.

## Use Cases

- VCs: Pre-screen technical founders
- Angels: Quick technical due diligence
- Developers: Self-assessment before fundraising
- Accelerators: Evaluate applicants at scale

## The Point

Most developer tools optimize for developers. This one optimizes for investors.

It answers the question investors actually ask: "Can this make money?" Not "Is this technically impressive?"

The difference matters. A technically mediocre solution to a billion-dollar problem beats a brilliant solution to a non-problem.

## Author

[@Siddhant-K-code](https://github.com/Siddhant-K-code)

---

**This tool provides analysis, not investment advice. Do your own diligence.**
