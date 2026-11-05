import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import Course, Lesson, LessonContent, Topic

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import seed_mock_data


def test_seed_data_is_idempotent_and_resettable():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    models = (Course, Lesson, Topic, LessonContent)
    expected_counts = (2, 8, 16, 16)

    try:
        seed_mock_data.seed_all_data(engine)
        seed_mock_data.seed_all_data(engine)
        with Session(engine) as session:
            actual_counts = tuple(
                session.scalar(select(func.count(model.id))) for model in models
            )
            for topic in session.scalars(select(Topic)):
                matching_contents = session.scalars(
                    select(LessonContent).where(
                        LessonContent.lesson_id == topic.lesson_id
                    )
                ).all()
                assert sum(
                    content.body.startswith(f"# {topic.name}\n\n")
                    for content in matching_contents
                ) == 1
        assert actual_counts == expected_counts

        seed_mock_data.seed_all_data(engine, reset=True)
        with Session(engine) as session:
            reset_counts = tuple(
                session.scalar(select(func.count(model.id))) for model in models
            )
        assert reset_counts == expected_counts
    finally:
        engine.dispose()


def test_cli_overrides_connection_configuration():
    args = seed_mock_data.parse_args(
        [
            "--host",
            "mysql-test",
            "--port",
            "3308",
            "--user",
            "test-user",
            "--password",
            "test-password",
            "--database",
            "test_database",
        ]
    )

    params = seed_mock_data.get_mysql_connection_params(args)
    url = seed_mock_data.create_database_url(params)

    assert url.host == "mysql-test"
    assert url.port == 3308
    assert url.username == "test-user"
    assert url.password == "test-password"
    assert url.database == "test_database"
