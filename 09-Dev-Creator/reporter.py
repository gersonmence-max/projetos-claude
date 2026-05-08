from datetime import datetime
from pathlib import Path


class Reporter:
    def generate(self, destination, spec, files, results, start_time):
        reports_dir = Path(destination) / "reports"
        reports_dir.mkdir(exist_ok=True)

        duration = (datetime.now() - start_time).total_seconds()
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        lines = [
            "# Dev Creator — Execution Report",
            f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Duration:** {duration:.1f}s",
            f"**Files created:** {len(successful)}/{len(files)}",
            "\n## Specification\n",
            f"```\n{spec[:1500]}\n```",
            "\n## Files Generated\n",
        ]

        for r in results:
            status = "OK" if r["success"] else "FAILED"
            attempts = r.get("attempts", 1)
            lines.append(f"- [{status}] `{r['path']}` ({attempts} attempt(s))")

        if failed:
            lines.append("\n## Failed Files\n")
            for r in failed:
                lines.append(f"- `{r['path']}`: {r.get('error', 'unknown error')}")

        content = "\n".join(lines) + "\n"
        report_path = reports_dir / "summary.md"
        report_path.write_text(content, encoding="utf-8")
        return str(report_path)
