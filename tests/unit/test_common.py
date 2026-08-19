from docs_buddy.common import sanitize_to_python_id


def test_normal_url_like():
    result = sanitize_to_python_id("github.com/programmer-ke/docs-buddy")
    assert result == "github_com_programmer_ke_docs_buddy"


def test_already_clean():
    result = sanitize_to_python_id("my_repo_123")
    assert result == "my_repo_123"


def test_leading_digit():
    result = sanitize_to_python_id("2fast")
    assert result == "name_2fast"


def test_mixed_special_digit_nonleading():
    result = sanitize_to_python_id("test-repo#1")
    assert result == "test_repo_1"


def test_all_special_chars():
    result = sanitize_to_python_id("@#$%")
    assert result == "____"
