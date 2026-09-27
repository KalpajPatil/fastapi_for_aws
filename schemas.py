from pydantic import BaseModel, ConfigDict, Field


class Geo(BaseModel):
    lat: str
    lng: str


class Address(BaseModel):
    street: str
    suite: str
    city: str
    zipcode: str
    geo: Geo


class Company(BaseModel):
    name: str
    catch_phrase: str = Field(alias="catchPhrase")
    bs: str

    model_config = ConfigDict(populate_by_name=True)


class UserSchema(BaseModel):
    id: int
    name: str
    username: str
    email: str
    phone: str
    website: str
    address: Address
    company: Company

    model_config = ConfigDict(from_attributes=True)
