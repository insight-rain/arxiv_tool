"""
Markdown Exporter - Export high-scoring papers to markdown format.

This module exports papers with relevance_score >= min_score to markdown files
in a separate directory, without modifying the original codebase.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models import Paper, Config
from fetcher import ArxivFetcher


class MarkdownExporter:
    """
    Export papers to markdown format.
    Uses ArxivFetcher to load papers, then exports them to markdown files.
    """
    
    def __init__(self, data_dir: str = "data/papers", output_dir: str = "data/markdown_export", config_path: str = "data/config.json"):
        """
        Initialize the exporter.
        
        Args:
            data_dir: Directory containing paper JSON files (default: "data/papers")
            output_dir: Output directory for markdown files (default: "data/markdown_export")
            config_path: Path to config.json file (default: "data/config.json")
        """
        self.fetcher = ArxivFetcher(data_dir=data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = Path(config_path)
    
    def export(self, min_score: float = 6.0, output_filename: str = None) -> dict:
        """
        Export papers with relevance_score >= min_score to individual markdown files.
        Creates a folder named after the date range, with one markdown file per paper.
        Papers are sorted by score from high to low (via filename prefix).
        
        Args:
            min_score: Minimum relevance score to export (default: 6.0)
            output_filename: Not used anymore, kept for compatibility
        
        Returns:
            dict with export statistics
        """
        export_time = datetime.now()
        
        # Load all papers
        all_papers = self.fetcher.list_papers(skip=0, limit=0)  # Load all papers
        
        # Load config to get date range
        start_date = None
        end_date = None
        if self.config_path.exists():
            try:
                config = Config.load(str(self.config_path))
                start_date = config.start_date
                end_date = config.end_date
                print(f"   📅 Filtering by date range: {start_date} to {end_date}")
            except Exception as e:
                print(f"   ⚠️  Could not load config for date filtering: {e}")
        
        if not start_date or not end_date:
            raise ValueError("Date range not found in config. Please ensure config.json has start_date and end_date.")
        
        # Filter papers with score >= min_score and within date range
        filtered_papers = []
        for p in all_papers:
            # Check score
            if p.relevance_score < min_score:
                continue
            
            # Check date range
            if p.published_date:
                try:
                    # Parse published_date (format: "2025-10-29T17:22:59Z" or "2025-10-29")
                    paper_date_str = p.published_date.split('T')[0]  # Extract date part
                    paper_date = datetime.strptime(paper_date_str, "%Y-%m-%d").date()
                    start = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end = datetime.strptime(end_date, "%Y-%m-%d").date()
                    
                    if not (start <= paper_date <= end):
                        continue  # Skip papers outside date range
                except Exception as e:
                    # If date parsing fails, include the paper (better to include than exclude)
                    pass
            
            filtered_papers.append(p)
        
        # Sort by relevance score (descending)
        filtered_papers.sort(key=lambda p: p.relevance_score, reverse=True)
        
        # Create folder name from date range
        folder_name = f"{start_date}_to_{end_date}"
        output_folder = self.output_dir / folder_name
        output_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📝 Exporting {len(filtered_papers)} papers with score >= {min_score} to folder: {folder_name}/")
        
        # Export each paper to a separate markdown file
        exported_count = 0
        failed_count = 0
        
        for idx, paper in enumerate(filtered_papers, 1):
            try:
                # Generate filename with score prefix for sorting
                # Use zero-padded index (already sorted by score) and score for display
                # Format score as zero-padded integer (multiply by 10) for proper string sorting
                # e.g., 8.5 -> 085, 9.0 -> 090, 6.2 -> 062
                score_padded = f"{int(paper.relevance_score * 10):03d}"  # Zero-padded to 3 digits
                index_str = f"{idx:03d}"  # Zero-padded index (001, 002, ...)
                
                # Sanitize paper title for filename (remove special characters)
                safe_title = "".join(c for c in paper.title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title.replace(' ', '_')
                if not safe_title:
                    safe_title = paper.id
                
                # Filename format: {index}_{score_padded}_{arxiv_id}_{title}.md
                # Index ensures proper sorting even if scores are equal
                filename = f"{index_str}_{score_padded}_{paper.id}_{safe_title}.md"
                output_path = output_folder / filename
                
                # Generate markdown content for single paper
                lines = []
                
                # Header with title
                lines.append(f"# {paper.title}\n")
                lines.append(f"**相关性评分**: {paper.relevance_score}/10\n")
                lines.append(f"**排名**: #{idx}\n")
                lines.append("")
                lines.append("---\n")
                lines.append("")
                
                # Add paper content
                paper_content = self._paper_to_markdown_content(paper)
                lines.append(paper_content)
                
                # Write to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(lines))
                
                exported_count += 1
                print(f"  ✓ Exported {paper.id} (score: {paper.relevance_score}/10) -> {filename}")
            except Exception as e:
                print(f"  ✗ Failed to process paper {paper.id}: {e}")
                failed_count += 1
                continue
        
        print(f"\n✅ Export completed!")
        print(f"   Total papers: {len(all_papers)}")
        print(f"   Exported: {exported_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Output folder: {output_folder}")
        
        return {
            "total_papers": len(all_papers),
            "exported_papers": exported_count,
            "failed_papers": failed_count,
            "min_score": min_score,
            "output_folder": str(output_folder),
            "date_range": f"{start_date}_to_{end_date}"
        }
    
    def _paper_to_markdown_content(self, paper: Paper) -> str:
        """Convert a Paper object to markdown content"""
        lines = []
        
        # Metadata
        lines.append("## 基本信息\n")
        lines.append(f"- **arXiv ID**: [{paper.id}]({paper.url})")
        lines.append(f"- **发布时间**: {paper.published_date or 'N/A'}")
        lines.append(f"- **相关性评分**: {paper.relevance_score}/10")
        lines.append(f"- **是否相关**: {'是' if paper.is_relevant else '否'}")
        lines.append("")
        
        # Authors
        if paper.authors:
            lines.append("## 作者\n")
            lines.append(", ".join(paper.authors))
            lines.append("")
        
        # Keywords
        if paper.extracted_keywords:
            lines.append("## 关键词\n")
            keywords_str = ", ".join([kw.replace("❌ ", "").replace("✅ ", "") for kw in paper.extracted_keywords])
            lines.append(keywords_str)
            lines.append("")
        
        # One-line summary
        if paper.one_line_summary:
            lines.append("## 一句话总结\n")
            lines.append(paper.one_line_summary)
            lines.append("")
        
        # Abstract
        lines.append("## 摘要\n")
        lines.append(paper.abstract)
        lines.append("")
        
        # Detailed summary (Stage 2 analysis)
        if paper.detailed_summary:
            lines.append("## 详细分析\n")
            lines.append(paper.detailed_summary)
            lines.append("")
        
        # Q&A pairs
        if paper.qa_pairs:
            lines.append("## 问答对\n")
            for idx, qa in enumerate(paper.qa_pairs, 1):
                lines.append(f"### 问题 {idx}\n")
                lines.append(f"**Q**: {qa.question}\n")
                
                if qa.thinking:
                    lines.append(f"**思考过程**:\n\n{qa.thinking}\n")
                
                lines.append(f"**A**: {qa.answer}\n")
                
                if qa.is_reasoning:
                    lines.append("*（使用推理模式生成）*\n")
                
                lines.append("")
        
        # Links
        lines.append("## 相关链接\n")
        lines.append(f"- [arXiv 页面]({paper.url})")
        if paper.html_url:
            lines.append(f"- [HTML 版本]({paper.html_url})")
        lines.append("")
        
        return "\n".join(lines)
    


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export high-scoring papers to markdown")
    parser.add_argument(
        "--min-score",
        type=float,
        default=6.0,
        help="Minimum relevance score to export (default: 6.0)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/markdown_export",
        help="Output directory for markdown file (default: data/markdown_export)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Output filename (if not provided, auto-generate with timestamp)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/papers",
        help="Directory containing paper JSON files (default: data/papers)"
    )
    parser.add_argument(
        "--config-path",
        type=str,
        default="data/config.json",
        help="Path to config.json file (default: data/config.json)"
    )
    
    args = parser.parse_args()
    
    exporter = MarkdownExporter(data_dir=args.data_dir, output_dir=args.output_dir, config_path=args.config_path)
    result = exporter.export(min_score=args.min_score, output_filename=args.output_file)
    
    print(f"\n📊 Export Statistics:")
    print(f"   Total papers: {result['total_papers']}")
    print(f"   Exported: {result['exported_papers']}")
    print(f"   Failed: {result['failed_papers']}")
    print(f"   Output file: {result['output_file']}")


if __name__ == "__main__":
    main()

