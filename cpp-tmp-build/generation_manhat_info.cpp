#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <future>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include <boost/range/iterator_range_core.hpp>
#include <boost/filesystem.hpp>

#include <libmmg/distances.hpp>
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

template <typename dist_t>
SymmetricDistanceMatrixAdapter<dist_t> make_distance_matrix(size_t size) {
	dist_t *data = new dist_t[size * (size - 1) / 2];
	return make_symmetric_distance_adapter(data, size);
}

template <typename Matr>
inline void write_matrix_row(std::ostream &stream, const Matr &matr, size_t i) {
	for (size_t j = 0; j < matr.cols(); ++j) {
		write_binary_raw(stream, to_storage_encoding(matr(i, j)));
	}
	stream.flush();
}

template <typename cgr_t>
inline void run(const vector<string> &filenames, const string &output_dir, int k) {
	size_t num_seqs = filenames.size();

	vector<vector<cgr_t>> cgrs(num_seqs);
	auto manhat_dists = make_distance_matrix<uint32_t>(num_seqs);
	auto info_dists = make_distance_matrix<float>(num_seqs);

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

		for (future<void> &x : results) {
			x.wait();
			bar.increment();
		}
	}

	{
		ProgressBar bar(num_seqs * (num_seqs - 1) / 2);
		ParallelExecutor exec;
		vector<future<void>> results;

		for (size_t i = 0; i < num_seqs; ++i) {
			results.push_back(exec.enqueue([&, i](unsigned _ignore) {
				for (size_t j = i + 1; j < num_seqs; ++j) {
					manhat_dists(i, j) = manhattan<uint32_t>(cgrs[i], cgrs[j]);
					info_dists(i, j) = approx_info_dist<float>(cgrs[i], cgrs[j]);
				}
			}));
		}

		exec.execute(thread::hardware_concurrency());

		ofstream out_manhat(output_dir + "/manhat.matr", ios::binary);
		ofstream out_info(output_dir + "/info.matr", ios::binary);

		for (size_t i = 0; i < num_seqs; ++i) {
			results[i].wait();

			write_matrix_row(out_manhat, manhat_dists, i);
			write_matrix_row(out_info, info_dists, i);

			bar.increment(num_seqs - i - 1);
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
