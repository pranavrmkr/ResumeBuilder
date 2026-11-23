from dataclasses import dataclass


@dataclass
class PersonalInfo:
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""
    summary: str = ""


@dataclass
class Education:
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    details: str = ""


@dataclass
class Experience:
    company: str = ""
    job_title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    achievements: str = ""


@dataclass
class Skill:
    name: str = ""
    category: str = "Technical Skills"
    proficiency: str = ""


@dataclass
class Project:
    title: str = ""
    description: str = ""
    technologies: str = ""
    contributions: str = ""
    url: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass
class Certification:
    name: str = ""
    issuer: str = ""
    date: str = ""
    url: str = ""


@dataclass
class Achievement:
    title: str = ""
    description: str = ""
    date: str = ""


@dataclass
class AdditionalInfo:
    languages: str = ""
    professional_links: str = ""
    portfolio: str = ""
    github: str = ""
    linkedin: str = ""
    extracurricular: str = ""
