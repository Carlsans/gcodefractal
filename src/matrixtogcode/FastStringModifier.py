import mmap
import os
from typing import Union, Tuple
import io


class FastStringModifier:
    """
    High-performance string modifier using memory mapping and optimized searching.
    """

    def __init__(self, input_string: Union[str, bytes]):
        # Convert string to bytes if necessary
        self.content = input_string.encode('utf-8') if isinstance(input_string, str) else input_string

        # Create a temporary memory-mapped file
        self.temp_file = io.BytesIO(self.content)
        self.size = len(self.content)

    def _find_line_start(self, target_line: int) -> int:
        """
        Binary search to find the start position of a line number.
        """
        if target_line == 0:
            return 0

        left, right = 0, self.size
        line_count = 0
        chunk_size = min(1024 * 1024, self.size)  # 1MB chunks

        # First, make a rough estimate of position
        estimated_pos = (target_line * self.size) // (self.size // 50)  # Estimate based on average line length
        estimated_pos = min(estimated_pos, self.size - chunk_size)

        # Read chunk at estimated position and count newlines
        chunk = self.content[estimated_pos:estimated_pos + chunk_size]
        newlines = chunk.count(b'\n')

        if newlines == 0:
            return estimated_pos

        # Adjust position based on newline count
        pos = estimated_pos
        while True:
            chunk = self.content[pos:pos + chunk_size]
            current_newlines = chunk.count(b'\n')

            if current_newlines >= target_line:
                # Found the chunk containing our line, now find exact position
                current_pos = pos
                line_count = 0
                for i, byte in enumerate(chunk):
                    if byte == ord(b'\n'):
                        line_count += 1
                        if line_count == target_line:
                            return current_pos + i + 1
                break

            pos += len(chunk)
            if pos >= self.size:
                return self.size - 1

        return pos

    def find_and_insert(self, start_line: int, pattern: str, insert_code: str) -> bytes:
        """
        Quickly find pattern after specified line and insert code.

        Args:
            start_line: Line number to start search from
            pattern: String pattern to search for
            insert_code: String to insert at pattern location

        Returns:
            Modified content as bytes
        """
        # Convert string parameters to bytes
        pattern_bytes = pattern.encode('utf-8')
        insert_code_bytes = insert_code.encode('utf-8')

        # Find start position of target line
        start_pos = self._find_line_start(start_line)

        # Search for pattern using memory-efficient chunk reading
        chunk_size = 1024 * 1024  # 1MB chunks
        pattern_pos = -1

        for chunk_start in range(start_pos, self.size, chunk_size):
            chunk_end = min(chunk_start + chunk_size + len(pattern_bytes), self.size)
            chunk = self.content[chunk_start:chunk_end]

            found_at = chunk.find(pattern_bytes)
            if found_at != -1:
                pattern_pos = chunk_start + found_at
                break

        if pattern_pos == -1:
            return self.content

        # Create modified content
        return self.content[:pattern_pos] + insert_code_bytes + self.content[pattern_pos:]


# Example usage
def modify_string_fast(large_string: str, start_line: int, pattern: str, insert_code: str) -> str:
    """
    High-performance wrapper function for string modification.

    Args:
        large_string: Input string to modify
        start_line: Line number to start search from
        pattern: Pattern to search for
        insert_code: Code to insert at pattern location

    Returns:
        Modified string
    """
    modifier = FastStringModifier(large_string)
    result = modifier.find_and_insert(start_line, pattern, insert_code)
    return result.decode('utf-8')