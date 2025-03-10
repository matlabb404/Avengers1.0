import React, { memo } from 'react';
import { View, FlatList } from 'react-native';
import styles from './Discover.style';
import PostCard from '@/components/Postcard/Postcard';

const thedata = [
  {
    id: '1',
    name: 'Jethro Danquah',
    description:
      'Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed.',
    review: 45,
    picture_url: [
      'https://images.pexels.com/photos/674010/pexels-photo-674010.jpeg',
    ],
  },
  {
    id: '2',
    name: 'Yaw Danquah',
    description:
      'Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed.',
    review: 40,
    picture_url: [
      'https://images.pexels.com/photos/674010/pexels-photo-674010.jpeg',
      'https://images.pexels.com/photos/3755222/pexels-photo-3755222.jpeg',
      'https://images.pexels.com/photos/3747259/pexels-photo-3747259.jpeg',
    ],
  },
  {
    id: '3',
    name: 'Yaw Danquah',
    description:
      'Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed.',
    review: 40,
    picture_url: [
      'https://images.pexels.com/photos/3755222/pexels-photo-3755222.jpeg',
      'https://images.pexels.com/photos/3747259/pexels-photo-3747259.jpeg',
      'https://images.pexels.com/photos/674010/pexels-photo-674010.jpeg',
    ],
  },
  {
    id: '4',
    name: 'Danquah',
    description:
      'Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed.',
    review: 50,
    picture_url: '',
  },
  {
    id: '5',
    name: 'Danquah',
    description:
      'Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed.',
    review: 50,
  },
    {
      id: '6',
      name: 'Jethro Danquah',
      description:
        'Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed.',
      review: 45,
      picture_url: [
        'https://images.pexels.com/photos/3755222/pexels-photo-3755222.jpeg',
      ],
    },
    {
      id: '7',
      name: 'Jethro Danquah',
      description:
        'Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed convallis Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed convallis, Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed convallis Lorem ipsum, dolor sit amet consectetur adipisicing elit. Blanditiis repudiandae laborum rem rerum eum porro, debitis, distinctio architecto quae in, velit officia ut corporis consectetur. Possimus, totam facilis. Vel, mollitia. Lorem ipsum dolor sit, amet consectetur adipisicing elit. Animi itaque eveniet sunt tempore libero, maiores dicta! Mollitia expedita ratione facere repellat vel non, voluptate necessitatibus odio quis? Doloribus, nemo sed. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed convallis',
      review: 45,
      picture_url: [
        'https://images.pexels.com/photos/3747259/pexels-photo-3747259.jpeg',
      ],
    },
    // Add more items if needed
  ];

  const Discover = () => {
    return (
      <View style={styles.discovermain}>
        <FlatList
          data={thedata}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <PostCard post={item} />}
          showsVerticalScrollIndicator={false} // Removes vertical scrollbar
        />
      </View>
    );
  };
  
  export default memo(Discover);