#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub信息抓取机器人
使用Playwright实现GitHub用户和项目信息的自动化抓取
"""

import asyncio
import argparse
import re
from playwright.async_api import async_playwright
from typing import Dict, List, Optional
import json


class GitHubBot:
    def __init__(self, proxy: Optional[str] = None):
        """
        初始化GitHub机器人
        
        Args:
            proxy: SOCKS5代理地址，格式: socks5://host:port
        """
        self.proxy = proxy
        self.browser = None
        self.page = None
        
    async def start_browser(self):
        """启动浏览器并等待用户登录"""
        playwright = await async_playwright().start()
        
        # 配置浏览器启动选项
        launch_options = {
            "headless": False,  # 显示浏览器窗口，方便用户登录
            "slow_mo": 100,  # 减慢操作速度，便于观察
        }
        
        # 如果提供了代理，添加到启动选项
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}
        
        self.browser = await playwright.chromium.launch(**launch_options)
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = await context.new_page()
        
        # 访问GitHub登录页面
        print("正在打开GitHub登录页面...")
        await self.page.goto("https://github.com/login", wait_until="networkidle")
        
        # 等待用户手动登录
        print("\n" + "="*60)
        print("请在浏览器中完成GitHub登录")
        print("登录完成后，请在终端按回车键继续...")
        print("="*60)
        input()
        
        # 验证是否已登录（检查是否有用户头像或用户名）
        try:
            await self.page.wait_for_selector('img[alt*="@"], [data-test-selector="user-nav"]', timeout=5000)
            print("✓ 检测到已登录状态")
        except:
            print("⚠ 警告: 可能未检测到登录状态，继续执行...")
    
    async def detect_type(self, input_str: str) -> str:
        """
        检测输入是用户名还是项目名
        
        Args:
            input_str: 输入的GitHub用户名或项目名
            
        Returns:
            'user' 或 'project'
        """
        # 如果包含斜杠，可能是项目名（格式：username/repo）
        if '/' in input_str and input_str.count('/') == 1:
            # 验证是否是有效的项目格式
            parts = input_str.split('/')
            if len(parts) == 2 and parts[0] and parts[1]:
                return 'project'
        
        # 访问URL判断
        url = f"https://github.com/{input_str}"
        await self.page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1)
        
        # 检查页面元素判断类型
        # 项目页面通常有 "Code"、"Issues"、"Pull requests" 等标签
        # 用户页面通常有 "Overview" 标签
        project_indicators = [
            'nav[role="navigation"] a[data-tab-item="code"]',
            'nav a[href*="/blob/"]',
            'nav a[href*="/tree/"]',
            'div[class*="repository"]',
            'span[itemprop="name"]',  # 项目名称
        ]
        
        user_indicators = [
            'nav[role="navigation"] a[data-tab-item="overview"]',
            'div[class*="user-profile"]',
            'img[alt*="@"]',  # 用户头像
        ]
        
        # 先检查是否是项目页面
        for selector in project_indicators:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    return 'project'
            except:
                continue
        
        # 再检查是否是用户页面
        for selector in user_indicators:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    return 'user'
            except:
                continue
        
        # 默认尝试作为用户处理
        return 'user'
    
    async def get_user_info(self, username: str) -> Dict:
        """
        获取GitHub用户信息
        
        Args:
            username: GitHub用户名
            
        Returns:
            包含用户信息的字典
        """
        print(f"\n正在获取用户 {username} 的信息...")
        url = f"https://github.com/{username}"
        await self.page.goto(url, wait_until="networkidle")
        
        info = {
            "username": username,
            "recent_commits": [],
            "repositories": [],
            "followers_count": 0
        }
        
        # 获取粉丝数
        try:
            # 尝试多种选择器
            selectors = [
                f'a[href="/{username}?tab=followers"]',
                'a[href*="tab=followers"]',
                'span[class*="Counter"]',
            ]
            followers_element = None
            for selector in selectors:
                try:
                    followers_element = await self.page.query_selector(selector)
                    if followers_element:
                        break
                except:
                    continue
            
            if followers_element:
                followers_text = await followers_element.inner_text()
                # 提取数字（可能包含K、M等单位）
                followers_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)', followers_text)
                if followers_match:
                    info["followers_count"] = followers_match.group(1)
        except Exception as e:
            print(f"获取粉丝数时出错: {e}")
        
        # 获取项目列表
        try:
            # 访问用户的仓库页面
            repos_url = f"https://github.com/{username}?tab=repositories"
            await self.page.goto(repos_url, wait_until="networkidle")
            await asyncio.sleep(2)  # 等待页面完全加载
            
            # 等待仓库列表加载，尝试多种选择器
            selectors = [
                'div[itemprop="owns"]',
                'li[itemprop="owns"]',
                'div[class*="repo"]',
            ]
            repo_elements = []
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    repo_elements = await self.page.query_selector_all(selector)
                    if repo_elements:
                        break
                except:
                    continue
            
            if not repo_elements:
                # 如果没找到，尝试更通用的选择器
                repo_elements = await self.page.query_selector_all('article, div[class*="Box"]')
            
            for repo_element in repo_elements[:10]:  # 限制前10个仓库
                try:
                    # 获取仓库名称
                    repo_link = await repo_element.query_selector('a[itemprop="name codeRepository"]')
                    if repo_link:
                        repo_name = await repo_link.inner_text()
                        repo_name = repo_name.strip()
                        repo_url = await repo_link.get_attribute('href')
                        
                        # 获取仓库描述
                        desc_element = await repo_element.query_selector('p[itemprop="description"]')
                        description = ""
                        if desc_element:
                            description = await desc_element.inner_text()
                            description = description.strip()
                        
                        # 获取语言和Star数
                        language_element = await repo_element.query_selector('span[itemprop="programmingLanguage"]')
                        language = ""
                        if language_element:
                            language = await language_element.inner_text()
                            language = language.strip()
                        
                        star_element = await repo_element.query_selector('a[href*="/stargazers"]')
                        star_count = "0"
                        if star_element:
                            star_text = await star_element.inner_text()
                            star_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)', star_text)
                            if star_match:
                                star_count = star_match.group(1)
                        
                        info["repositories"].append({
                            "name": repo_name,
                            "url": f"https://github.com{repo_url}",
                            "description": description,
                            "language": language,
                            "stars": star_count
                        })
                except Exception as e:
                    print(f"处理仓库时出错: {e}")
                    continue
        except Exception as e:
            print(f"获取项目列表时出错: {e}")
        
        # 获取最近的提交记录
        try:
            # 访问用户的贡献页面或活动页面
            activity_url = f"https://github.com/{username}"
            await self.page.goto(activity_url, wait_until="networkidle")
            
            # 尝试获取活动feed中的提交记录
            commit_elements = await self.page.query_selector_all('div[class*="TimelineItem"]')
            
            for commit_element in commit_elements[:5]:  # 限制前5条
                try:
                    commit_text = await commit_element.inner_text()
                    if "committed" in commit_text.lower() or "pushed" in commit_text.lower():
                        # 提取提交信息
                        lines = commit_text.split('\n')
                        commit_info = {
                            "message": lines[0] if lines else "",
                            "details": commit_text[:200]  # 限制长度
                        }
                        info["recent_commits"].append(commit_info)
                except:
                    continue
        except Exception as e:
            print(f"获取提交记录时出错: {e}")
        
        return info
    
    async def get_project_info(self, project_name: str) -> Dict:
        """
        获取GitHub项目信息
        
        Args:
            project_name: GitHub项目名（格式：username/repo）
            
        Returns:
            包含项目信息的字典
        """
        print(f"\n正在获取项目 {project_name} 的信息...")
        url = f"https://github.com/{project_name}"
        await self.page.goto(url, wait_until="networkidle")
        
        info = {
            "project": project_name,
            "readme": "",
            "recent_commits": [],
            "contributors": [],
            "stars": "0"
        }
        
        # 获取Star数
        try:
            # 尝试多种选择器
            star_selectors = [
                'a[href*="/stargazers"]',
                'a[href*="stargazers"]',
                'span[id*="repo-stars"]',
                'button[aria-label*="star"]',
            ]
            
            for selector in star_selectors:
                try:
                    star_element = await self.page.query_selector(selector)
                    if star_element:
                        star_text = await star_element.inner_text()
                        star_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)', star_text)
                        if star_match:
                            info["stars"] = star_match.group(1)
                            break
                except:
                    continue
        except Exception as e:
            print(f"获取Star数时出错: {e}")
        
        # 获取README内容
        try:
            # 先访问项目主页
            await self.page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 尝试多种README选择器
            readme_selectors = [
                'div[data-testid="readme-content"]',
                'article.markdown-body',
                '#readme',
                'div[class*="readme"]',
                'div[class*="markdown"]',
            ]
            
            readme_text = ""
            for selector in readme_selectors:
                try:
                    readme_element = await self.page.query_selector(selector)
                    if readme_element:
                        readme_text = await readme_element.inner_text()
                        if readme_text and len(readme_text) > 50:  # 确保获取到有效内容
                            break
                except:
                    continue
            
            if readme_text:
                info["readme"] = readme_text[:5000]  # 限制长度
        except Exception as e:
            print(f"获取README时出错: {e}")
        
        # 获取最近的提交记录
        try:
            commits_url = f"https://github.com/{project_name}/commits"
            await self.page.goto(commits_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 等待提交列表加载，尝试多种选择器
            commit_selectors = [
                'ol[class*="commits-list"]',
                'div[class*="commit-group"]',
                'li[class*="commit"]',
                'div[class*="commit-group-item"]',
                'div.Box-row',
            ]
            
            commit_elements = []
            for selector in commit_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    commit_elements = await self.page.query_selector_all(selector)
                    if commit_elements:
                        break
                except:
                    continue
            
            for commit_element in commit_elements[:10]:  # 限制前10条
                try:
                    # 获取提交信息
                    commit_link = await commit_element.query_selector('a[href*="/commit/"]')
                    commit_message = ""
                    commit_author = ""
                    commit_date = ""
                    
                    if commit_link:
                        commit_message = await commit_link.inner_text()
                        commit_message = commit_message.strip()
                    
                    # 获取提交人
                    author_element = await commit_element.query_selector('a[href*="/"][class*="commit-author"]')
                    if not author_element:
                        author_element = await commit_element.query_selector('a[rel="author"]')
                    if author_element:
                        commit_author = await author_element.inner_text()
                        commit_author = commit_author.strip()
                    
                    # 获取提交日期
                    date_element = await commit_element.query_selector('relative-time, time-ago')
                    if date_element:
                        commit_date = await date_element.get_attribute('datetime') or await date_element.inner_text()
                    
                    if commit_message:
                        info["recent_commits"].append({
                            "message": commit_message,
                            "author": commit_author,
                            "date": commit_date
                        })
                except Exception as e:
                    continue
        except Exception as e:
            print(f"获取提交记录时出错: {e}")
        
        # 获取贡献者列表
        try:
            contributors_url = f"https://github.com/{project_name}/graphs/contributors"
            await self.page.goto(contributors_url, wait_until="networkidle")
            
            await asyncio.sleep(2)
            
            contributor_elements = await self.page.query_selector_all('a[href*="/"][class*="contributor"]')
            
            for contributor_element in contributor_elements[:10]:  # 限制前10个贡献者
                try:
                    contributor_name = await contributor_element.inner_text()
                    contributor_name = contributor_name.strip()
                    if contributor_name:
                        info["contributors"].append(contributor_name)
                except:
                    continue
        except Exception as e:
            print(f"获取贡献者列表时出错: {e}")
        
        return info
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
    
    def print_user_info(self, info: Dict):
        """打印用户信息"""
        print("\n" + "="*60)
        print("GitHub用户信息")
        print("="*60)
        print(f"用户名: {info['username']}")
        print(f"粉丝数: {info['followers_count']}")
        
        print(f"\n项目列表 (共 {len(info['repositories'])} 个):")
        for i, repo in enumerate(info['repositories'], 1):
            print(f"\n{i}. {repo['name']}")
            print(f"   URL: {repo['url']}")
            if repo['description']:
                print(f"   描述: {repo['description']}")
            if repo['language']:
                print(f"   语言: {repo['language']}")
            print(f"   Stars: {repo['stars']}")
        
        print(f"\n最近的提交记录 (共 {len(info['recent_commits'])} 条):")
        for i, commit in enumerate(info['recent_commits'], 1):
            print(f"\n{i}. {commit.get('message', 'N/A')}")
            if commit.get('details'):
                print(f"   详情: {commit['details'][:100]}...")
    
    def print_project_info(self, info: Dict):
        """打印项目信息"""
        print("\n" + "="*60)
        print("GitHub项目信息")
        print("="*60)
        print(f"项目: {info['project']}")
        print(f"Stars: {info['stars']}")
        
        if info['readme']:
            print(f"\nREADME内容 (前500字符):")
            print("-" * 60)
            print(info['readme'][:500])
            if len(info['readme']) > 500:
                print("...")
            print("-" * 60)
        
        print(f"\n最近的提交记录 (共 {len(info['recent_commits'])} 条):")
        for i, commit in enumerate(info['recent_commits'], 1):
            print(f"\n{i}. {commit.get('message', 'N/A')}")
            if commit.get('author'):
                print(f"   提交人: {commit['author']}")
            if commit.get('date'):
                print(f"   日期: {commit['date']}")
        
        if info['contributors']:
            print(f"\n贡献者列表 (共 {len(info['contributors'])} 个):")
            for i, contributor in enumerate(info['contributors'], 1):
                print(f"{i}. {contributor}")


async def main():
    parser = argparse.ArgumentParser(description='GitHub信息抓取机器人')
    parser.add_argument('input', help='GitHub用户名或项目名（格式：username/repo）')
    parser.add_argument('--proxy', '-p', help='SOCKS5代理地址，格式：socks5://host:port', default=None)
    parser.add_argument('--output', '-o', help='输出JSON文件路径（可选）', default=None)
    
    args = parser.parse_args()
    
    bot = GitHubBot(proxy=args.proxy)
    
    try:
        # 启动浏览器并等待登录
        await bot.start_browser()
        
        # 检测输入类型
        input_type = await bot.detect_type(args.input)
        print(f"\n检测到输入类型: {input_type}")
        
        # 根据类型获取信息
        if input_type == 'user':
            info = await bot.get_user_info(args.input)
            bot.print_user_info(info)
        else:
            info = await bot.get_project_info(args.input)
            bot.print_project_info(info)
        
        # 如果指定了输出文件，保存JSON
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()
        print("\n浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
