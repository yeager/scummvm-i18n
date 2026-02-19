/*
 * Minimal .mo file reader — Proof of Concept for ScummVM i18n migration
 *
 * Reads GNU gettext .mo files (little-endian and big-endian) and provides
 * a lookup interface compatible with ScummVM's TranslationManager.
 *
 * Reference: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html
 */

#ifndef MO_READER_H
#define MO_READER_H

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

class MoReader {
public:
	MoReader() = default;
	~MoReader() = default;

	/**
	 * Load a .mo file from a memory buffer.
	 * @param data Pointer to the .mo file content.
	 * @param size Size in bytes.
	 * @return true on success.
	 */
	bool load(const uint8_t *data, size_t size);

	/**
	 * Load a .mo file from disk.
	 * @param path File path.
	 * @return true on success.
	 */
	bool loadFromFile(const std::string &path);

	/**
	 * Look up a translation for msgid.
	 * Returns empty string if not found.
	 */
	const std::string &getTranslation(const std::string &msgid) const;

	/**
	 * Look up a translation with context (msgctxt\x04msgid encoding).
	 */
	const std::string &getTranslation(const std::string &msgid, const std::string &context) const;

	/** Number of loaded strings. */
	size_t size() const { return _translations.size(); }

private:
	uint32_t read32(const uint8_t *p) const;

	bool _needSwap = false;
	std::unordered_map<std::string, std::string> _translations;
	static const std::string _empty;
};

#endif // MO_READER_H
