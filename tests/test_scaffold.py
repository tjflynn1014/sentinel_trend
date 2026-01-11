from sentinel_trend.ops.cli import main


def test_import_sentinel_trend() -> None:
    import sentinel_trend

    assert sentinel_trend is not None


def test_cli_outputs_expected_message(capsys) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "sentinel_trend: scaffold OK"
