"""
Bu dosyada LLM'den beklenen yapılandırılmış çıktılar ve analiz sonuç modelleri tanımlanır.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Experience(BaseModel):
    role: str
    company: str = ""
    summary: str = Field("", description="Bu görevde yapılanların en fazla 1 cümlelik özeti")
    start_year: int = Field(0, description="Göreve başlangıç yılı (örn. 2022), bilinmiyorsa 0")
    end_year: int = Field(0, description="Bitiş yılı; hâlâ devam ediyorsa veya bilinmiyorsa 0")


class CVProfile(BaseModel):
    name: str = ""
    title: str = ""
    years_experience: float = Field(0, description="Toplam profesyonel deneyim (yıl)")
    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class JobSkills(BaseModel):
    required_skills: list[str] = Field(
        default_factory=list,
        description="'Aranan nitelikler' bölümündeki teknik beceri/teknoloji adları (kısa, standart)",
    )
    nice_to_have_skills: list[str] = Field(
        default_factory=list,
        description="'Artı puan'/'tercih sebebi' bölümündeki beceriler ve nitelikler",
    )


class JobProfile(JobSkills):
    title: str = ""
    company: str = Field("", description="İşvereni/şirket adı (başlıkta veya metinde geçer)")
    min_years_experience: float = 0
    responsibilities: list[str] = Field(default_factory=list)


class SkillEvidence(BaseModel):
    skill: str
    status: Literal["matched", "uncertain", "missing"]
    evidence: str = ""
    similarity: float = 0.0
    source: Literal["cv", "user", "none"] = "none"


class MatchResult(BaseModel):
    score: int
    experience_factor: float
    required: list[SkillEvidence]
    nice_to_have: list[SkillEvidence]

    def by_status(self, status: str, *, required: bool = True) -> list[SkillEvidence]:
        items = self.required if required else self.nice_to_have
        return [s for s in items if s.status == status]


class GapItem(BaseModel):
    skill: str
    severity: Literal["yüksek", "orta", "düşük"]
    how_to_frame: str = Field(description="Başvuruda bu eksiği nasıl ele almalı")
    learning_suggestion: str = Field(description="Kısa, uygulanabilir öğrenme önerisi")


class GapPlan(BaseModel):
    items: list[GapItem] = Field(default_factory=list)


class Critique(BaseModel):
    is_grounded: bool = Field(description="Ön yazıdaki tüm iddialar CV ile destekleniyor mu")
    unsupported_claims: list[str] = Field(default_factory=list)
    feedback: str = ""


class InterviewQuestion(BaseModel):
    question: str
    why_asked: str
    answer_tip: str


class InterviewPrep(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)
