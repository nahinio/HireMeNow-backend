from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.course import RecommendedCourseResponse


class SkillCreate(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True


class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class SkillQuizSummary(BaseModel):
    quiz_id: UUID
    pass_threshold: int
    question_count: int


class SkillPublicResponse(BaseModel):
    id: UUID
    name: str
    description: str
    quiz: SkillQuizSummary | None = None


class SkillListResponse(BaseModel):
    items: list[SkillPublicResponse]
    page: int
    limit: int
    total: int


class AnswerOptionPublicResponse(BaseModel):
    id: UUID
    question_id: UUID
    body: str


class QuizQuestionPublicResponse(BaseModel):
    id: UUID
    quiz_id: UUID
    body: str
    position: int
    options: list[AnswerOptionPublicResponse]


class QuizPublicDetailResponse(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str
    pass_threshold: int
    questions: list[QuizQuestionPublicResponse]


class QuizCreate(BaseModel):
    skill_id: UUID
    pass_threshold: int = 80
    published: bool = False


class QuizUpdate(BaseModel):
    pass_threshold: int | None = Field(default=None, ge=0, le=100)
    published: bool | None = None


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
    recommended_courses: list[RecommendedCourseResponse] = Field(default_factory=list)


class BulkQuizOptionCreate(BaseModel):
    body: str
    is_correct: bool = False


class BulkQuizQuestionCreate(BaseModel):
    body: str
    position: int = Field(ge=1)
    options: list[BulkQuizOptionCreate] = Field(min_length=4, max_length=4)


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class SkillQuizReplace(BaseModel):
    pass_threshold: int = Field(default=80, ge=0, le=100)
    published: bool = False
    questions: list[BulkQuizQuestionCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_questions(self) -> Self:
        positions = [question.position for question in self.questions]
        if len(positions) != len(set(positions)):
            raise ValueError("Question positions must be unique")

        for question in self.questions:
            correct_count = sum(1 for option in question.options if option.is_correct)
            if correct_count != 1:
                raise ValueError(
                    f"Question at position {question.position} must have exactly one correct option"
                )
        return self


class AdminSkillSummary(BaseModel):
    id: UUID
    name: str
    description: str
    is_active: bool
    quiz_id: UUID | None = None
    pass_threshold: int | None = None
    published: bool | None = None
    question_count: int = 0


class AdminSkillListResponse(BaseModel):
    items: list[AdminSkillSummary]
    page: int
    limit: int
    total: int


class SkillWithQuizCreate(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True
    pass_threshold: int = Field(default=80, ge=0, le=100)
    published: bool = False
    questions: list[BulkQuizQuestionCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_questions(self) -> Self:
        positions = [question.position for question in self.questions]
        if len(positions) != len(set(positions)):
            raise ValueError("Question positions must be unique")

        for question in self.questions:
            correct_count = sum(1 for option in question.options if option.is_correct)
            if correct_count != 1:
                raise ValueError(
                    f"Question at position {question.position} must have exactly one correct option"
                )
        return self


class SkillWithQuizQuestionResponse(BaseModel):
    id: UUID
    body: str
    position: int
    options: list[AnswerOptionResponse]

    model_config = {"from_attributes": True}


class AdminSkillDetailResponse(BaseModel):
    skill: SkillResponse
    quiz: QuizResponse | None = None
    questions: list[SkillWithQuizQuestionResponse] = Field(default_factory=list)


class SkillWithQuizResponse(BaseModel):
    skill: SkillResponse
    quiz: QuizResponse
    questions: list[SkillWithQuizQuestionResponse]

    @classmethod
    def from_records(cls, skill, quiz, question_records) -> "SkillWithQuizResponse":
        return cls(
            skill=SkillResponse.model_validate(skill),
            quiz=QuizResponse(
                id=quiz.id,
                skill_id=quiz.skill_id,
                skill_name=skill.name,
                pass_threshold=quiz.pass_threshold,
                published=quiz.published,
            ),
            questions=[
                SkillWithQuizQuestionResponse(
                    id=question.id,
                    body=question.body,
                    position=question.position,
                    options=[
                        AnswerOptionResponse.model_validate(option)
                        for option in options
                    ],
                )
                for question, options in question_records
            ],
        )
