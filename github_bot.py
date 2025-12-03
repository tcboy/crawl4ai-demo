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

# 超时时间配置（毫秒）
PAGE_LOAD_TIMEOUT = 120000  # 120秒
SELECTOR_TIMEOUT = 10000    # 10秒


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
    
    async def goto_with_retry(self, url: str, wait_until: str = "load"):
        """
        带重试机制的页面加载方法
        
        Args:
            url: 要访问的URL
            wait_until: 等待条件，默认为 load（更快）
        """
        # 如果当前页面已经是目标URL，直接返回
        current_url = self.page.url.rstrip('/')
        target_url = url.rstrip('/')
        if current_url == target_url:
            print(f"  页面已在目标URL，跳过加载")
            return
        
        # 根据wait_until参数选择等待策略
        if wait_until == "networkidle":
            wait_options = ["networkidle", "load", "domcontentloaded"]
            timeouts = [30000, 60000, PAGE_LOAD_TIMEOUT]  # 30秒, 60秒, 120秒
        elif wait_until == "load":
            wait_options = ["load", "domcontentloaded"]
            timeouts = [60000, PAGE_LOAD_TIMEOUT]  # 60秒, 120秒
        else:
            wait_options = [wait_until]
            timeouts = [PAGE_LOAD_TIMEOUT]
        
        for i, wait_type in enumerate(wait_options):
            timeout = timeouts[min(i, len(timeouts)-1)]
            try:
                print(f"  尝试加载页面 (等待条件: {wait_type}, 超时: {timeout/1000}秒)...")
                await self.page.goto(url, wait_until=wait_type, timeout=timeout)
                print(f"  ✓ 页面加载成功 ({wait_type})")
                return
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower():
                    if i < len(wait_options) - 1:
                        print(f"  ⚠ {wait_type} 超时，尝试下一个策略...")
                    else:
                        print(f"  ⚠ {wait_type} 超时，尝试使用最短等待...")
                else:
                    print(f"  ⚠ {wait_type} 失败: {error_msg[:100]}")
                
                if wait_type == wait_options[-1]:
                    # 最后一个选项也失败了，尝试使用最短等待
                    print("  尝试使用最短等待时间...")
                    try:
                        await self.page.goto(url, wait_until="commit", timeout=10000)
                        print("  ✓ 页面已加载（使用最短等待）")
                        return
                    except:
                        # 如果还是失败，抛出原始异常
                        raise e
                # 尝试下一个选项
                continue
        
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
        print(f"超时时间设置为: {PAGE_LOAD_TIMEOUT/1000}秒")
        await self.goto_with_retry("https://github.com/login", wait_until="networkidle")
        
        # 等待用户手动登录
        print("\n" + "="*60)
        print("请在浏览器中完成GitHub登录")
        print("登录完成后，请在终端按回车键继续...")
        print("="*60)
        input()
        
        # 刷新页面以确保获取最新状态
        print("正在刷新页面以检测登录状态...")
        await self.page.reload(wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        await asyncio.sleep(2)
        
        # 验证是否已登录（使用多种选择器检查）
        login_indicators = [
            'img[alt*="@"]',  # 用户头像
            '[data-test-selector="user-nav"]',  # 用户导航
            'summary[aria-label*="profile"]',  # 用户菜单
            'button[aria-label*="profile"]',  # 用户按钮
            'a[href*="/settings"]',  # 设置链接
            'nav[aria-label="User account"]',  # 用户账户导航
            'details[data-view-component="true"] summary[aria-label*="View profile"]',  # GitHub新界面
            'button[aria-label*="View profile"]',  # 查看资料按钮
        ]
        
        logged_in = False
        for selector in login_indicators:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    print(f"✓ 检测到已登录状态 (通过选择器: {selector[:50]}...)")
                    logged_in = True
                    break
            except:
                continue
        
        # 如果没找到，尝试检查URL是否跳转到主页（登录后通常会跳转）
        if not logged_in:
            current_url = self.page.url
            if "github.com" in current_url and "/login" not in current_url:
                print("✓ 检测到已离开登录页面，假设已登录")
                logged_in = True
        
        if not logged_in:
            print("⚠ 警告: 可能未检测到登录状态，但将继续执行...")
            print("   如果后续操作失败，请确保已正确登录")
    
    async def detect_type(self, input_str: str) -> str:
        """
        检测输入是用户名还是项目名
        
        Args:
            input_str: 输入的GitHub用户名或项目名
            
        Returns:
            'user' 或 'project'
        """
        print(f"正在访问: https://github.com/{input_str}")
        
        # 如果包含斜杠，可能是项目名（格式：username/repo）
        if '/' in input_str and input_str.count('/') == 1:
            # 验证是否是有效的项目格式
            parts = input_str.split('/')
            if len(parts) == 2 and parts[0] and parts[1]:
                print("根据格式判断为项目（包含斜杠）")
                return 'project'
        
        # 访问URL判断 - 使用更快的加载策略
        url = f"https://github.com/{input_str}"
        page_loaded = False
        try:
            print(f"正在访问页面...")
            # 先尝试快速加载（domcontentloaded）
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                print("  ✓ 页面DOM已加载")
                page_loaded = True
            except Exception as e1:
                print(f"  ⚠ DOM加载超时，尝试其他方式...")
                # 如果失败，尝试使用goto_with_retry
                try:
                    await self.goto_with_retry(url, wait_until="load")
                    page_loaded = True
                except Exception as e2:
                    print(f"  ⚠ 页面加载失败: {e2}")
            
            if page_loaded:
                print("等待页面内容渲染...")
                await asyncio.sleep(3)  # 等待页面内容渲染
        except Exception as e:
            print(f"⚠ 访问页面时出错: {e}")
            print("将尝试根据URL格式判断类型")
            # 如果访问失败，根据格式判断
            if '/' in input_str:
                return 'project'
            return 'user'
        
        # 检查页面元素判断类型
        # 使用更精确的检测方法
        
        print("正在检测页面类型...")
        
        # 方法1: 检查URL路径结构
        current_url = self.page.url
        print(f"  当前URL: {current_url}")
        
        # 项目页面的URL格式: https://github.com/username/repo
        # 用户页面的URL格式: https://github.com/username 或 https://github.com/username?tab=...
        url_parts = current_url.replace("https://github.com/", "").split("/")
        if len(url_parts) >= 2 and url_parts[1] and not url_parts[1].startswith("?"):
            # URL中有两个部分（username/repo），很可能是项目
            print(f"  ✓ 根据URL结构判断为项目页面 (路径: /{url_parts[0]}/{url_parts[1]})")
            return 'project'
        elif len(url_parts) == 1 or (len(url_parts) >= 1 and url_parts[0] and not url_parts[0].startswith("?")):
            # URL只有一个部分（username），很可能是用户
            print(f"  ✓ 根据URL结构判断为用户页面 (路径: /{url_parts[0]})")
            return 'user'
        
        # 方法2: 检查页面标题
        try:
            title = await self.page.title()
            print(f"  页面标题: {title}")
            # 项目页面标题通常包含仓库名，用户页面通常包含 "GitHub" 和用户名
            if " · GitHub" in title and "/" in input_str:
                # 如果标题中有斜杠分隔，可能是项目
                if title.count(" · ") >= 2:
                    print("  ✓ 根据页面标题判断为项目页面")
                    return 'project'
        except:
            pass
        
        # 方法3: 检查特定的页面元素（使用更精确的选择器）
        # 项目页面特有的元素
        project_indicators = [
            'nav[role="navigation"] a[data-tab-item="code"]',  # Code标签
            'nav[role="navigation"] a[data-tab-item="issues"]',  # Issues标签
            'nav[role="navigation"] a[data-tab-item="pull-requests"]',  # PR标签
            'button[data-tab-item="code"]',  # Code按钮
            'a[href*="/blob/main"]',  # 代码文件链接
            'a[href*="/tree/main"]',  # 目录树链接
        ]
        
        # 用户页面特有的元素
        user_indicators = [
            'nav[role="navigation"] a[data-tab-item="overview"]',  # Overview标签
            'nav[role="navigation"] a[data-tab-item="repositories"]',  # Repositories标签
            'div[class*="pinned-item-list"]',  # 置顶项目列表
            'div[class*="user-profile"]',  # 用户资料区域
            'div[class*="profile-rollup"]',  # 用户活动汇总
        ]
        
        # 先检查项目页面特征（更具体的选择器）
        project_score = 0
        for selector in project_indicators:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    project_score += len(elements)
                    print(f"  找到项目特征: {selector[:50]}... (数量: {len(elements)})")
            except:
                continue
        
        # 再检查用户页面特征
        user_score = 0
        for selector in user_indicators:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    user_score += len(elements)
                    print(f"  找到用户特征: {selector[:50]}... (数量: {len(elements)})")
            except:
                continue
        
        print(f"  检测得分 - 项目: {project_score}, 用户: {user_score}")
        
        # 根据得分判断
        if project_score > user_score and project_score > 0:
            print("  ✓ 根据页面元素判断为项目页面")
            return 'project'
        elif user_score > project_score and user_score > 0:
            print("  ✓ 根据页面元素判断为用户页面")
            return 'user'
        
        # 方法4: 如果都没检测到，根据输入格式判断
        print("未检测到明确的页面特征，根据输入格式判断")
        if '/' in input_str:
            return 'project'
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
        print("正在加载用户主页...")
        await self.goto_with_retry(url, wait_until="load")  # 使用load更快
        await asyncio.sleep(2)  # 等待页面内容渲染
        
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
        print("正在获取项目列表...")
        try:
            # 访问用户的仓库页面
            repos_url = f"https://github.com/{username}?tab=repositories"
            await self.goto_with_retry(repos_url, wait_until="load")  # 使用load更快
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
                    await self.page.wait_for_selector(selector, timeout=SELECTOR_TIMEOUT)
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
        print("正在获取最近的提交记录...")
        try:
            # 访问用户的贡献页面或活动页面
            activity_url = f"https://github.com/{username}"
            await self.goto_with_retry(activity_url, wait_until="load")  # 使用load更快
            await asyncio.sleep(2)  # 等待页面内容渲染
            
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
        print("正在加载项目主页...")
        await self.goto_with_retry(url, wait_until="load")  # 使用load而不是networkidle，更快
        await asyncio.sleep(2)  # 等待页面内容渲染
        
        info = {
            "project": project_name,
            "readme": "",
            "recent_commits": [],
            "contributors": [],
            "stars": "0"
        }
        
        # 获取Star数
        print("正在获取Star数...")
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
                            print(f"  ✓ Star数: {info['stars']}")
                            break
                except:
                    continue
        except Exception as e:
            print(f"获取Star数时出错: {e}")
        
        # 获取README内容（已经在项目主页，不需要重新加载）
        print("正在获取README内容...")
        try:
            
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
        print("正在获取最近的提交记录...")
        try:
            commits_url = f"https://github.com/{project_name}/commits"
            await self.goto_with_retry(commits_url, wait_until="load")  # 使用load更快
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
                    await self.page.wait_for_selector(selector, timeout=SELECTOR_TIMEOUT)
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
        print("正在获取贡献者列表...")
        try:
            contributors_url = f"https://github.com/{project_name}/graphs/contributors"
            await self.goto_with_retry(contributors_url, wait_until="load")  # 使用load更快
            
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
        print("="*60)
        print("步骤 1/4: 启动浏览器并等待登录")
        print("="*60)
        await bot.start_browser()
        print("✓ 浏览器启动完成，登录检测完成\n")
        
        # 检测输入类型
        print("="*60)
        print("步骤 2/4: 检测输入类型")
        print("="*60)
        print(f"正在分析输入: {args.input}")
        input_type = await bot.detect_type(args.input)
        print(f"✓ 检测到输入类型: {input_type}\n")
        
        # 根据类型获取信息
        print("="*60)
        print(f"步骤 3/4: 获取{'用户' if input_type == 'user' else '项目'}信息")
        print("="*60)
        if input_type == 'user':
            info = await bot.get_user_info(args.input)
            bot.print_user_info(info)
        else:
            info = await bot.get_project_info(args.input)
            bot.print_project_info(info)
        print("\n✓ 信息获取完成\n")
        
        # 如果指定了输出文件，保存JSON
        if args.output:
            print("="*60)
            print("步骤 4/4: 保存结果")
            print("="*60)
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            print(f"✓ 结果已保存到: {args.output}\n")
        
        print("="*60)
        print("所有任务完成！")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n正在关闭浏览器...")
        await bot.close()
        print("浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
