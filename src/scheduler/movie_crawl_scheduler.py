import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.movie_service import movie_service

logger = logging.getLogger(__name__)

def start_movie_crawl_scheduler():
    """
    启动电影数据采集调度器
    """
    scheduler = BackgroundScheduler()
    
    # 每天凌晨2:00执行电影爬取任务
    scheduler.add_job(
        func=movie_service.schedule_seedhub_crawl,
        args=[2, "电影"],
        trigger=CronTrigger(hour=2, minute=0),
        id='seedhub_movie_crawl',
        name='爬取SeedHub电影数据',
        replace_existing=True
    )
    
    # 每天凌晨2:30执行电视剧爬取任务
    scheduler.add_job(
        func=movie_service.schedule_seedhub_crawl,
        args=[2, "电视剧"],
        trigger=CronTrigger(hour=2, minute=30),
        id='seedhub_tv_crawl',
        name='爬取SeedHub电视剧数据',
        replace_existing=True
    )
    
    # 每天凌晨3:00执行动漫爬取任务
    scheduler.add_job(
        func=movie_service.schedule_seedhub_crawl,
        args=[2, "动漫"],
        trigger=CronTrigger(hour=3, minute=0),
        id='seedhub_anime_crawl',
        name='爬取SeedHub动漫数据',
        replace_existing=True
    )
    
    # 每天凌晨3:30执行热门电影爬取任务
    scheduler.add_job(
        func=movie_service.schedule_seedhub_hot_crawl,
        args=[1],
        trigger=CronTrigger(hour=3, minute=30),
        id='seedhub_hot_crawl',
        name='爬取SeedHub热门电影数据',
        replace_existing=True
    )
    
    # 每天凌晨4:00执行新上映电影爬取任务
    scheduler.add_job(
        func=movie_service.schedule_seedhub_new_crawl,
        args=[1],
        trigger=CronTrigger(hour=4, minute=0),
        id='seedhub_new_crawl',
        name='爬取SeedHub新上映电影数据',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("电影数据采集调度器已启动")
