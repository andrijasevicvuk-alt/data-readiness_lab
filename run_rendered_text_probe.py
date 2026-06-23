from src.ypi_source_lab.rendered_text_probe import (
    CSV_OUTPUT,
    JSON_OUTPUT,
    DEFAULT_RENDERED_TEXT_PROBE_RESULTS,
    write_rendered_text_probe_results,
)


def main() -> int:
    write_rendered_text_probe_results(DEFAULT_RENDERED_TEXT_PROBE_RESULTS)
    print("Wrote rendered text probe results to:")
    print(JSON_OUTPUT)
    print(CSV_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
