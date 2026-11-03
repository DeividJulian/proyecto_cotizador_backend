from pydantic import BaseModel, Field


class SectionText(BaseModel):
    heading: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20000)


class ProposalSectionsUpdate(BaseModel):
    sections: list[SectionText] = Field(min_length=1)


class ProposalOut(BaseModel):
    quote_id: int
    proposal: str
