#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <future>
#include <iostream>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

#include <boost/range/iterator_range_core.hpp>
#include <boost/filesystem.hpp>

#include <libmmg/io.hpp>
#include <libmmg/representations.hpp>
#include <libmmg/utils.hpp>

// clang-format off
#include <src/mmg-cli/progress_bar.hpp>
#include <src/mmg-cli/progress_bar.cpp>
// clang-format on

using namespace std;
using namespace mmg;
namespace fs = boost::filesystem;

template <typename cgr_t>
inline void run(const vector<string> &filenames, const string &output_dir, int k) {
	size_t num_seqs = filenames.size();

	vector<vector<cgr_t>> cgrs(num_seqs);

	{
		ProgressBar bar(num_seqs);
		ParallelExecutor exec;
		vector<future<void>> results;

		for (size_t i = 0; i < num_seqs; ++i) {
			results.push_back(exec.enqueue([&, i](unsigned _ignore) {
				ifstream file(filenames[i]);
				vector<string> seqs = read_fasta(file);
				cgrs[i] = cgr<cgr_t>(seqs.front(), k);
			}));
		}

		exec.execute(thread::hardware_concurrency());

		ofstream out_cgrs(output_dir + "/cgrs.matr", ios::binary);
		if (is_same<cgr_t, uint16_t>::value) {
			write_binary_raw<uint8_t>(out_cgrs, 16);
		} else if (is_same<cgr_t, uint32_t>::value) {
			write_binary_raw<uint8_t>(out_cgrs, 32);
		}
		write_binary_raw<uint64_t>(out_cgrs, num_seqs);

		for (size_t i = 0; i < num_seqs; ++i) {
			results[i].wait();
			write_array_binary(out_cgrs, cgrs[i].data(), cgrs[i].size());
			out_cgrs.flush();
			bar.increment();
		}
	}
}

int main(int argc, char *argv[]) {
	vector<string> filenames;
	for (auto &entry : boost::make_iterator_range(fs::directory_iterator(argv[3]), {})) {
		filenames.push_back(absolute(entry.path()).string());
	}
	sort(filenames.begin(), filenames.end());

	cout << "Detected " << thread::hardware_concurrency() << " threads" << endl << endl;

	if ("16"s == argv[1]) {
		run<uint16_t>(filenames, argv[4], atoi(argv[2]));
	} else if ("32"s == argv[1]) {
		run<uint32_t>(filenames, argv[4], atoi(argv[2]));
	}

	return 0;
}
