import os
from dotenv import load_dotenv
import requests
import time
import json
import base64
from typing import List, Dict, Optional
from dataclasses import dataclass
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()

@dataclass
class Repository:
    """Data class to store repository information"""
    name: str
    description: str
    url: str
    stars: int
    language: str
    created_at: str
    updated_at: str
    readme_content: str
    topics: List[str]
    is_fork: bool
    watchers: int
    open_issues: int

class GitHubAnalyzer:
    """Enhanced GitHub API interactions with better error handling"""

    def __init__(self, github_token: Optional[str] = None):
        self.session = requests.Session()
        self.base_url = "https://api.github.com"

        # Set up headers with authentication if token provided
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Repository-Investment-Analyzer"
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
            print("✓ Using authenticated GitHub access (higher rate limits)")
        else:
            print("⚠️  Using unauthenticated GitHub access (lower rate limits)")

        self.session.headers.update(self.headers)

    def get_user_repositories(self, username: str, exclude_forks: bool = True,
                            min_stars: int = 0, max_repos: int = None,
                            fetch_mode: str = "all") -> List[Repository]:
        """Fetch repositories for a given user with smart fetching based on mode"""
        repos = []
        page = 1

        print(f"\n🔍 Fetching repositories for user: {username}")
        print(f"   Filters: exclude_forks={exclude_forks}, min_stars={min_stars}")

        # Determine fetch strategy based on mode
        if fetch_mode == "recent":
            # For recent, we only need to fetch the first 10-20 non-fork repos
            max_to_fetch = 20  # Fetch a bit more to account for forks
            print(f"   📚 Smart fetch: Getting most recent ~{max_to_fetch} repos only")
        elif fetch_mode == "popular":
            # For popular, we need all repos to sort by stars
            max_to_fetch = max_repos
            print(f"   📊 Full fetch needed: Must get all repos to find most popular by stars")
        elif fetch_mode == "top20":
            # For top20, we need all repos to sort by stars
            max_to_fetch = max_repos
            print(f"   📊 Full fetch needed: Must get all repos to find top 20 by stars")
        elif fetch_mode == "active":
            # For active, fetch recent 50 to find 15 active ones
            max_to_fetch = 50
            print(f"   📅 Smart fetch: Getting recent ~{max_to_fetch} repos to find active ones")
        else:  # "all"
            max_to_fetch = max_repos
            if max_repos:
                print(f"   Max repositories to fetch: {max_repos}")

        while True:
            # Check if we've reached our fetch limit
            if max_to_fetch and len(repos) >= max_to_fetch:
                break

            url = f"{self.base_url}/users/{username}/repos"
            params = {
                "page": page,
                "per_page": 100,
                "sort": "updated",  # GitHub returns most recently updated first
                "direction": "desc"
            }

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()

                # Check rate limit
                self._check_rate_limit(response)

                data = response.json()

                if not data:
                    break

                for repo_data in data:
                    # Check if we've reached our fetch limit
                    if max_to_fetch and len(repos) >= max_to_fetch:
                        break

                    # Apply filters
                    if exclude_forks and repo_data.get("fork", False):
                        continue

                    if repo_data.get("stargazers_count", 0) < min_stars:
                        continue

                    # Fetch README content
                    readme_content = self._fetch_readme(username, repo_data["name"])

                    # Fetch additional repository details
                    repo_details = self._fetch_repo_details(username, repo_data["name"])

                    # Add sleep to avoid rate limiting
                    time.sleep(0.5)

                    repo = Repository(
                        name=repo_data["name"],
                        description=repo_data.get("description") or "No description",
                        url=repo_data["html_url"],
                        stars=repo_data.get("stargazers_count", 0),
                        language=repo_data.get("language") or "Unknown",
                        created_at=repo_data["created_at"],
                        updated_at=repo_data["updated_at"],
                        readme_content=readme_content,
                        topics=repo_details.get("topics", []),
                        is_fork=repo_data.get("fork", False),
                        watchers=repo_data.get("watchers_count", 0),
                        open_issues=repo_data.get("open_issues_count", 0)
                    )

                    repos.append(repo)
                    print(f"  ✓ Fetched: {repo.name} ({repo.stars} ⭐, {repo.language})")

                page += 1

                # Sleep between pages
                time.sleep(1)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"❌ User not found: {username}")
                else:
                    print(f"❌ HTTP Error: {e}")
                break
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching repositories: {e}")
                break

        print(f"\n📊 Summary:")
        print(f"   Total repositories fetched: {len(repos)}")
        if fetch_mode == "recent" and len(repos) < 30:
            print(f"   ⚡ Time saved: Only fetched {len(repos)} repos instead of all user repos")
        elif fetch_mode == "active" and len(repos) < 100:
            print(f"   🚀 Smart fetch: Checked {len(repos)} recent repos for active ones")
        print(f"   Total stars: {sum(r.stars for r in repos)}")
        # Filter out None and 'Unknown' languages
        languages = set(r.language for r in repos if r.language and r.language != 'Unknown')
        print(f"   Languages: {', '.join(languages) if languages else 'No languages detected'}")

        return repos

    def _fetch_readme(self, username: str, repo_name: str) -> str:
        """Fetch README content for a repository"""
        readme_url = f"{self.base_url}/repos/{username}/{repo_name}/readme"

        try:
            response = self.session.get(readme_url)

            if response.status_code == 200:
                content = response.json().get("content", "")
                # Decode base64 content
                if content:
                    decoded = base64.b64decode(content).decode('utf-8')
                    # Limit README to first 3000 characters to save tokens
                    return decoded[:3000] if len(decoded) > 3000 else decoded

            return "No README available"

        except Exception as e:
            return f"Error fetching README: {str(e)}"

    def _fetch_repo_details(self, username: str, repo_name: str) -> Dict:
        """Fetch additional repository details"""
        url = f"{self.base_url}/repos/{username}/{repo_name}"

        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}

    def _check_rate_limit(self, response):
        """Check and display rate limit information"""
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset_time = response.headers.get('X-RateLimit-Reset')

        if remaining:
            if int(remaining) < 10:
                reset_dt = datetime.fromtimestamp(int(reset_time), tz=timezone.utc)
                print(f"⚠️  Rate limit low: {remaining} requests remaining. Resets at {reset_dt}")

                if int(remaining) < 5:
                    wait_time = (reset_dt - datetime.now(timezone.utc)).total_seconds()
                    if wait_time > 0:
                        print(f"⏸️  Waiting {wait_time:.0f} seconds for rate limit reset...")
                        time.sleep(wait_time + 1)

class InvestmentAnalyzer:
    """Enhanced analyzer with better prompting and caching"""

    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        # Use the latest model for better analysis
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def analyze_repositories(self, repos: List[Repository], focus_area: str = "all",
                            analysis_depth: str = "comprehensive") -> Dict:
        """Analyze repositories with customizable focus areas and depth"""

        # Store original count for reporting
        original_count = len(repos)

        # Apply additional filtering based on focus area
        # Note: Some filtering already happened during fetch for efficiency
        if focus_area == "popular":
            # Need to sort all fetched repos by stars
            repos = sorted(repos, key=lambda x: x.stars, reverse=True)[:10]
            print(f"   Analyzing top 10 most popular repos")
        elif focus_area == "recent":
            # Already fetched recent ones, just take first 10
            repos = repos[:10]
            print(f"   Analyzing 10 most recently updated repos")
        elif focus_area == "top20":
            # Need to sort all fetched repos by stars
            repos = sorted(repos, key=lambda x: x.stars, reverse=True)[:20]
            print(f"   Analyzing top 20 repos by stars")
        elif focus_area == "active":
            # Filter for actively maintained repos (updated in last 6 months)
            six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
            active_repos = []
            for r in repos:
                try:
                    # Parse the ISO format date from GitHub
                    updated = datetime.fromisoformat(r.updated_at.replace('Z', '+00:00'))
                    if updated > six_months_ago:
                        active_repos.append(r)
                except Exception as e:
                    # If date parsing fails, skip this repo
                    continue
            repos = sorted(active_repos, key=lambda x: x.stars, reverse=True)[:15]
            print(f"   Analyzing {len(repos)} actively maintained repos")
        else:  # "all"
            if len(repos) > 30:
                print(f"   Note: Analyzing all {len(repos)} repos. This may take longer and use more API tokens.")
                print("   Consider using 'popular', 'recent', or 'active' focus for faster analysis.")

        # Prepare repository data for analysis
        repo_summaries = []
        for repo in repos:
            summary = f"""
Repository: {repo.name}
URL: {repo.url}
Description: {repo.description}
Stars: {repo.stars} | Watchers: {repo.watchers} | Open Issues: {repo.open_issues}
Language: {repo.language}
Topics: {', '.join(repo.topics) if repo.topics else 'None'}
Created: {repo.created_at}
Last Updated: {repo.updated_at}

README Preview:
{repo.readme_content[:1500]}
---
"""
            repo_summaries.append(summary)

        # Adjust prompt based on analysis depth
        if analysis_depth == "quick":
            prompt = self._get_quick_analysis_prompt(repo_summaries, len(repos))
        else:
            prompt = self._get_comprehensive_analysis_prompt(repo_summaries, len(repos), original_count)

        try:
            print("\n🤖 Analyzing repositories with Gemini AI...")
            print(f"   Analysis depth: {analysis_depth}")
            print("   This may take a moment...")

            response = self.model.generate_content(prompt)

            return {
                "analysis": response.text,
                "total_repos_analyzed": len(repos),
                "total_repos_fetched": original_count,
                "focus_area": focus_area,
                "analysis_depth": analysis_depth,
                "timestamp": datetime.now().isoformat(),
                "model_used": "gemini-2.5-flash-lite"
            }

        except Exception as e:
            print(f"❌ Error during AI analysis: {e}")
            return {
                "error": str(e),
                "total_repos_analyzed": len(repos),
                "timestamp": datetime.now().isoformat()
            }

    def _get_quick_analysis_prompt(self, repo_summaries: List[str], count: int) -> str:
        """Quick analysis prompt for faster results"""
        return f"""
You are a venture capital analyst doing a quick portfolio scan.

Quickly analyze these {count} repositories and provide:

## TOP 3 INVESTMENT OPPORTUNITIES
For each:
- Project name and one-line pitch
- Why it's fundable (2 sentences max)
- Market size potential
- Investment score (X/10)

## DEVELOPER PROFILE
- Key strengths (bullet points)
- Best project to focus on for funding

## QUICK VERDICT
- Portfolio Grade: [A-F]
- Ready for funding? [Yes/No/6 months]
- Recommended next step

REPOSITORIES:
{''.join(repo_summaries)}

Be concise and actionable. Focus only on the most promising opportunities.
"""

    def _get_comprehensive_analysis_prompt(self, repo_summaries: List[str], analyzed_count: int, total_count: int) -> str:
        """Comprehensive analysis prompt for detailed insights"""

        context = f"Analyzing {analyzed_count} repositories"
        if analyzed_count < total_count:
            context += f" (selected from {total_count} total repositories)"

        return f"""
You are a senior venture capital partner at a top-tier VC firm evaluating GitHub repositories for investment potential.

{context}

EVALUATION CRITERIA:
1. **Problem-Solution Fit**: Does it solve a real, painful problem?
2. **Market Size**: TAM/SAM/SOM potential
3. **Technical Innovation**: Novel approach or significant improvement
4. **Competitive Advantage**: Moat, defensibility, unique insights
5. **Team Capability**: Code quality, documentation, development velocity
6. **Traction Indicators**: Stars, community engagement, adoption signals
7. **Monetization Potential**: Clear path to revenue
8. **Scalability**: Technical and business model scalability

REPOSITORIES TO ANALYZE:
{''.join(repo_summaries)}

DELIVERABLES:

## 🏆 TOP INVESTMENT OPPORTUNITIES (Max 5)
For each high-potential project:
- **Project**: [Name] - [One-line pitch]
- **Investment Thesis**: [2-3 sentences on why this is fundable]
- **Market Opportunity**: [Specific market size or growth potential]
- **Unique Value Prop**: [What makes this different/better]
- **Revenue Model**: [How this could make money]
- **Risk Factors**: [Top 2-3 concerns]
- **Next Steps**: [What developer needs to do to be investment-ready]
- **Investment Score**: [X/10] with brief justification
- **Funding Stage**: [Pre-seed/Seed/Series A readiness]

## 🌟 PROJECTS TO WATCH (Max 3)
Brief mentions of projects with potential but need more development.

## 👤 DEVELOPER PROFILE
- **Technical Strengths**: [Key competencies demonstrated]
- **Domain Expertise**: [Industries/areas of focus]
- **Entrepreneurial Indicators**: [Signs of business acumen]
- **Red Flags**: [Any concerns for investors]

## 💡 STRATEGIC RECOMMENDATIONS
1. **Priority Project**: Which ONE project should they focus on for fundraising
2. **Key Improvements**: Top 3 things to do before approaching investors
3. **Missing Elements**: What VCs expect but isn't present
4. **Positioning Strategy**: How to pitch themselves to investors

## 🎯 INVESTMENT VERDICT
- **Portfolio Grade**: [A-F] with explanation
- **Funding Readiness**: [Not Ready / 3-6 months / Ready Now]
- **Potential Check Size**: [$X at Y valuation]
- **Best Investor Type**: [Angel / Seed VC / Accelerator / Corporate VC]

Be specific, actionable, and realistic. Focus on commercial viability over technical impressiveness.
"""

def main():
    """Enhanced main execution with better UX"""

    # ASCII Art Header
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     GitHub Repository Investment Analyzer 🚀     ║
    ║         Find VC-Worthy Projects in GitHub        ║
    ╚══════════════════════════════════════════════════╝
    """)

    # Get configuration from environment or user input
    github_token = os.getenv("GITHUB_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not github_token:
        use_token = input("Would you like to use a GitHub token for better rate limits? (y/n): ").lower()
        if use_token == 'y':
            github_token = input("Enter GitHub token: ").strip()

    if not gemini_api_key:
        gemini_api_key = input("Enter Gemini API key: ").strip()
        if not gemini_api_key:
            print("❌ Gemini API key is required!")
            return

    # Get analysis parameters
    username = input("\n📝 Enter GitHub username to analyze: ").strip()

    print("\n🎯 Analysis Focus:")
    print("1. All repositories (comprehensive - fetches all)")
    print("2. Most popular (top 10 by stars - needs to fetch all)")
    print("3. Recently active (top 10 by update - ⚡ FAST, only fetches ~20)")
    print("4. Top 20 repositories (by stars - needs to fetch all)")
    print("5. Actively maintained (last 6 months - 🚀 SMART, fetches ~50)")

    focus_choice = input("Select focus area (1-5, default=3 for fastest): ").strip() or "3"
    focus_map = {
        "1": "all",
        "2": "popular",
        "3": "recent",
        "4": "top20",
        "5": "active"
    }
    focus_area = focus_map.get(focus_choice, "recent")  # Default to recent (fastest)

    # Ask about analysis depth
    print("\n📊 Analysis Depth:")
    print("1. Quick scan (faster, key insights only)")
    print("2. Comprehensive (detailed investment analysis)")

    depth_choice = input("Select analysis depth (1-2, default=2): ").strip() or "2"
    analysis_depth = "quick" if depth_choice == "1" else "comprehensive"

    # Repository filters
    min_stars = input("\n⭐ Minimum stars filter (default=0): ").strip()
    min_stars = int(min_stars) if min_stars.isdigit() else 0

    # Max repos for "all" option or when needing all repos
    max_repos = None
    if focus_area == "all":
        max_input = input("Maximum repositories to fetch (default=all, suggested=50): ").strip()
        if max_input.isdigit():
            max_repos = int(max_input)
    elif focus_area in ["popular", "top20"]:
        # For popular/top20, we might want to limit total repos to check
        max_input = input("Maximum repositories to check (default=all, press Enter to skip): ").strip()
        if max_input.isdigit():
            max_repos = int(max_input)

    # Initialize components
    print("\n⚙️  Initializing components...")
    github_analyzer = GitHubAnalyzer(github_token)
    investment_analyzer = InvestmentAnalyzer(gemini_api_key)

    # Smart fetching info
    if focus_area == "recent":
        print("   💡 Fast mode: Will only fetch ~20 recent repos (not all)")
    elif focus_area == "active":
        print("   💡 Smart mode: Will fetch ~50 recent repos to find active ones")
    elif focus_area in ["popular", "top20"]:
        print("   ⚠️  Note: Need to fetch all repos to sort by popularity")

    # Fetch repositories with smart fetching based on focus area
    repos = github_analyzer.get_user_repositories(
        username,
        exclude_forks=True,
        min_stars=min_stars,
        max_repos=max_repos,
        fetch_mode=focus_area  # Pass the focus area for smart fetching
    )

    if not repos:
        print(f"❌ No repositories found for user: {username}")
        return

    # Analyze repositories
    analysis_result = investment_analyzer.analyze_repositories(
        repos,
        focus_area=focus_area,
        analysis_depth=analysis_depth
    )

    # Generate and save report
    if "error" not in analysis_result:
        print("\n" + "="*60)
        print("📊 INVESTMENT ANALYSIS RESULTS")
        print("="*60)
        print(analysis_result["analysis"])

        # Save reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save markdown report
        md_filename = f"report_{username}_{timestamp}.md"
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(f"# Investment Analysis: {username}\n\n")
            f.write(f"Generated: {analysis_result['timestamp']}\n")
            f.write(f"Repositories Analyzed: {analysis_result['total_repos_analyzed']}")
            if analysis_result.get('total_repos_fetched'):
                f.write(f" (from {analysis_result['total_repos_fetched']} fetched)")
            f.write(f"\nFocus: {analysis_result['focus_area']}\n")
            f.write(f"Analysis Depth: {analysis_result['analysis_depth']}\n\n")
            f.write(analysis_result["analysis"])

        # Save JSON data
        json_filename = f"report_{username}_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2)

        print(f"\n✅ Reports saved:")
        print(f"   📄 Markdown: {md_filename}")
        print(f"   📄 JSON: {json_filename}")

        print("\n🎉 Analysis complete! Review the reports for investment insights.")
    else:
        print(f"\n❌ Analysis failed: {analysis_result['error']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Analysis cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
