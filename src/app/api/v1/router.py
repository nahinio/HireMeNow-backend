from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    client,
    conversations,
    freelancer,
    freelancers,
    jobs,
    quizzes,
    reports,
    reviews,
    courses,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(freelancer.router)
api_router.include_router(freelancers.router)
api_router.include_router(client.router)
api_router.include_router(admin.router)
api_router.include_router(quizzes.router)
api_router.include_router(courses.router)
api_router.include_router(jobs.router)
api_router.include_router(conversations.router)
api_router.include_router(reviews.router)
api_router.include_router(reports.router)
