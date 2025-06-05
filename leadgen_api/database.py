from sqlmodel import Session, SQLModel, create_engine

engine = create_engine("sqlite:///leadgen.db")


def init_db() -> None:
	SQLModel.metadata.create_all(engine)


def get_session() -> Session:
	with Session(engine) as session:
	    yield session
