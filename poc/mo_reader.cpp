/*
 * Minimal .mo file reader — Proof of Concept for ScummVM i18n migration
 *
 * .mo binary format (v0):
 *   Offset  Size   Description
 *   0x00    4      Magic number: 0x950412de (LE) or 0xde120495 (BE)
 *   0x04    4      Revision (major<<16 | minor)
 *   0x08    4      N — number of strings
 *   0x0C    4      O — offset of original string table
 *   0x10    4      T — offset of translation string table
 *   0x14    4      S — size of hashing table
 *   0x18    4      H — offset of hashing table
 *
 *   Original/Translation tables: N entries of { uint32 length, uint32 offset }
 *   Strings are NUL-terminated at data[offset], length bytes long (excluding NUL).
 *
 *   Context is encoded as "msgctxt\x04msgid" in the original string.
 */

#include "mo_reader.h"
#include <cstring>
#include <fstream>

const std::string MoReader::_empty;

static constexpr uint32_t MO_MAGIC_LE = 0x950412de;
static constexpr uint32_t MO_MAGIC_BE = 0xde120495;

uint32_t MoReader::read32(const uint8_t *p) const {
	uint32_t v;
	std::memcpy(&v, p, 4);
	if (_needSwap) {
		v = ((v >> 24) & 0xFF) | ((v >> 8) & 0xFF00) |
		    ((v << 8) & 0xFF0000) | ((v << 24) & 0xFF000000);
	}
	return v;
}

bool MoReader::load(const uint8_t *data, size_t size) {
	if (size < 28) return false;

	uint32_t magic;
	std::memcpy(&magic, data, 4);

	if (magic == MO_MAGIC_LE) {
		_needSwap = false;
	} else if (magic == MO_MAGIC_BE) {
		_needSwap = true;
	} else {
		return false;
	}

	uint32_t revision = read32(data + 4);
	uint32_t major = revision >> 16;
	if (major > 1) return false;  // unknown major revision

	uint32_t nstrings = read32(data + 8);
	uint32_t origTableOff = read32(data + 12);
	uint32_t transTableOff = read32(data + 16);

	_translations.clear();
	_translations.reserve(nstrings);

	for (uint32_t i = 0; i < nstrings; ++i) {
		uint32_t oLen = read32(data + origTableOff + i * 8);
		uint32_t oOff = read32(data + origTableOff + i * 8 + 4);
		uint32_t tLen = read32(data + transTableOff + i * 8);
		uint32_t tOff = read32(data + transTableOff + i * 8 + 4);

		if (oOff + oLen >= size || tOff + tLen >= size) return false;

		std::string orig(reinterpret_cast<const char *>(data + oOff), oLen);
		std::string trans(reinterpret_cast<const char *>(data + tOff), tLen);

		// Skip the metadata entry (empty msgid)
		if (!orig.empty()) {
			_translations[std::move(orig)] = std::move(trans);
		}
	}

	return true;
}

bool MoReader::loadFromFile(const std::string &path) {
	std::ifstream f(path, std::ios::binary | std::ios::ate);
	if (!f) return false;

	auto size = f.tellg();
	f.seekg(0);

	std::vector<uint8_t> buf(static_cast<size_t>(size));
	f.read(reinterpret_cast<char *>(buf.data()), size);

	return load(buf.data(), buf.size());
}

const std::string &MoReader::getTranslation(const std::string &msgid) const {
	auto it = _translations.find(msgid);
	return (it != _translations.end()) ? it->second : _empty;
}

const std::string &MoReader::getTranslation(const std::string &msgid, const std::string &context) const {
	// .mo files encode context as "context\x04msgid"
	std::string key = context + '\x04' + msgid;
	auto it = _translations.find(key);
	if (it != _translations.end()) return it->second;

	// Fallback: try without context
	return getTranslation(msgid);
}
