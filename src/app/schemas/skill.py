from uuid import UUID

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str
    is_active: bool = True


class SkillResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class QuizCreate(BaseModel):
    skill_id: UUID
    pass_threshold: int = 80
    published: bool = False


class QuizResponse(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str | None = None
    pass_threshold: int
    published: bool

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    body: str
    position: int


class QuestionResponse(BaseModel):
    id: UUID
    quiz_id: UUID
    body: str
    position: int

    model_config = {"from_attributes": True}


class AnswerOptionCreate(BaseModel):
    body: str
    is_correct: bool = False


class AnswerOptionResponse(BaseModel):
    id: UUID
    question_id: UUID
    body: str
    is_correct: bool

    model_config = {"from_attributes": True}


class QuizAttemptAnswer(BaseModel):
    question_id: UUID
    selected_option_id: UUID


class QuizAttemptRequest(BaseModel):
    answers: list[QuizAttemptAnswer]


class QuizAttemptResponse(BaseModel):
    result: str
    score: float
    resources: list[str] = Field(default_factory=list)
