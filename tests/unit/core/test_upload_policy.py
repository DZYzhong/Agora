from packages.core.upload_policy import (
    POLICY_VERSION,
    UploadTier,
    classify_upload,
    contains_secret,
    redact_sensitive,
    revalidate_path,
    revalidate_remote,
    revalidate_upload,
)


def test_low_tier_for_structured_summary_without_excerpts():
    assessment = classify_upload(
        kind="development_update",
        has_source_excerpt=False,
        secret_rule_exception=False,
        forbidden_path_or_type=False,
        over_default_limit=False,
        policy_override=False,
        quality_waiver=False,
    )
    assert assessment.tier is UploadTier.LOW
    assert assessment.requires_grant is False
    assert assessment.policy_version == POLICY_VERSION


def test_high_tier_for_source_excerpt():
    assessment = classify_upload(kind="context_proposal", has_source_excerpt=True)
    assert assessment.tier is UploadTier.HIGH
    assert assessment.requires_grant is True
    assert "source_or_document_excerpt" in assessment.reasons


def test_high_tier_for_each_high_risk_signal():
    for kwargs in (
        {"secret_rule_exception": True},
        {"forbidden_path_or_type": True},
        {"over_default_limit": True},
        {"policy_override": True},
        {"quality_waiver": True},
    ):
        assessment = classify_upload(kind="context_proposal", **kwargs)
        assert assessment.tier is UploadTier.HIGH, kwargs


def test_unknown_kind_is_high_tier():
    assessment = classify_upload(kind="arbitrary_blob")
    assert assessment.tier is UploadTier.HIGH
    assert "unknown_payload_kind" in assessment.reasons


def test_client_claimed_low_tier_cannot_downgrade_high_payload():
    # The tier is computed from the payload signals; a client cannot pass a
    # self-claimed tier. Re-classifying the same signals always yields HIGH.
    assessment = classify_upload(kind="context_proposal", has_source_excerpt=True, quality_waiver=True)
    assert assessment.tier is UploadTier.HIGH
    assert assessment.reasons == ("source_or_document_excerpt", "quality_waiver")


def test_revalidate_path_rejects_absolute_traversal_and_secrets():
    assert "absolute_or_backslash_path" in revalidate_path("/etc/passwd")
    assert "absolute_or_backslash_path" in revalidate_path("C:\\windows\\x")
    assert "traversal_or_empty_segment" in revalidate_path("../secret")
    assert "traversal_or_empty_segment" in revalidate_path("a/../b")
    assert "traversal_or_empty_segment" in revalidate_path("a//b")
    assert "control_character" in revalidate_path("src/\x00null.py")
    assert "path_contains_credentials_or_secret_pattern" in revalidate_path("https://user:pass@example.com/x")
    assert revalidate_path("src/payments/state_machine.py") == []


def test_revalidate_upload_combines_violations():
    violations = revalidate_upload(
        kind="development_update",
        paths=["src/ok.py", "/etc/passwd"],
        changed_files=9999,
        agent_summary="x" * (8 * 1024 + 1),
    )
    assert "absolute_or_backslash_path" in violations
    assert "changed_files_over_limit" in violations
    assert "agent_summary_over_limit" in violations


def test_revalidate_upload_accepts_clean_payload():
    violations = revalidate_upload(
        kind="development_update",
        paths=["src/ok.py", "tests/test_ok.py"],
        changed_files=2,
        agent_summary="summary",
        test_result="pytest passed",
    )
    assert violations == []


def test_revalidate_upload_rejects_unknown_kind():
    assert "unknown_payload_kind" in revalidate_upload(kind="blob")


def test_revalidate_remote_rejects_credentialized_remote():
    assert "credentialized_remote" in revalidate_remote("https://dev:top-secret@git.example.cn/x.git")
    assert revalidate_remote("git@example.com:team/x.git") == []


def test_contains_secret_detects_secret_like_values():
    assert contains_secret("export AWS_ACCESS_KEY_ID=AKIA...")
    assert contains_secret("-----BEGIN RSA PRIVATE KEY-----")
    assert contains_secret("password=hunter2")
    assert not contains_secret("changed payment state machine")


def test_redact_sensitive_removes_credentials():
    redacted = redact_sensitive(
        "Authorization: Bearer abc123 cookie: agora_session=xyz; remote=https://dev:top-secret@host/x.git"
    )
    assert "abc123" not in redacted
    assert "xyz" not in redacted
    assert "top-secret" not in redacted
    assert "***REDACTED***" in redacted
